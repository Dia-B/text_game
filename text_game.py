from tkinter import Tk, Toplevel, Entry, BooleanVar, BOTTOM, TOP, LEFT, RIGHT
from tkinter.scrolledtext import ScrolledText
import re
import safe_parser as sp

from scriptc import parse_file, is_varname, ETC_KEY, KEYWORDS

from script_data import ALLOWED_CALLS, DEFAULT_SCRIPT

USER_COLOUR = "white"
SYS_COLOUR = "green"
SCREEN_COLOUR = "black"

#ETC_KEY = r"[^\S\s]"

#KEYWORDS = ["qkey", "assign", "repqtext", "qtext", "allowed"]

def main(filename):
    root = Tk()
    root.title("Chatbox")
    root.geometry("1000x1000")
    
    root.wait_visibility(root)
    root.attributes('-alpha', 0.9)
    
    chat = Entry(root, background=SCREEN_COLOUR, foreground=USER_COLOUR, font=("courier new", 16))
    chat.bind("<Return>", user_input)
    
    chat.display = ScrolledText(root, state="disabled", background=SCREEN_COLOUR, font=("courier new", 20))
    chat.display.tag_configure("call", foreground=SYS_COLOUR)
    chat.display.tag_configure("response", foreground=USER_COLOUR)
    
    chat.receiving = BooleanVar(value=False)
    
    # geometry
    chat.pack(fill="x", side=BOTTOM)
    chat.display.pack(fill="both", expand=True)
    chat.focus_set()
    
    init(chat, parse_file(filename))
    
    root.mainloop()

def flush(textwid, text, tag):
    textwid.configure(state="normal")
    text = text.encode("utf-8").decode("unicode_escape")
    textwid.insert("end", text + "\n", tag)
    textwid.configure(state="disabled")
    textwid.see("end")

def user_input(event):
    wid = event.widget
    text = wid.get()
    wid.delete(0, "end")
    
    if not wid.receiving.get():
        return
    
    flush(wid.display, text, "response")
    wid.receiving.set(False)
    
    wid.after(50, respond, (wid, text.strip()))

# accepts (roughly) state, response, outputs state, internal action, new question
# how should state be formatted? will at least have qkey, qtext, allowed

def init(chat, qscript):
    chat.qscript = qscript
    start_key = "start"
    
    chat.state = {
        "qkey":start_key,
        "assign":[],
        "repqtext":None,
        "$counter$":1
    } # start state
    
    chat.state.update(chat.qscript[start_key])
    
    qtext = process_text(chat.state["qtext"], chat.state)
    
    flush(chat.display, qtext, "call")
    chat.receiving.set(True)

def respond(bundle):
    chat, response = bundle
    
    state = chat.state
    state["$response$"] = response
    
    # try to get future key, is response expected?
    # we want to avoid this being impure as much as possible
    
    key, match = get_key(state["allowed"], response, state)
    
    if key == None: # couldn't find a way to proceed
        if state["repqtext"] != None: # on failure, is there a repqtext?
            qtext = process_text(state["repqtext"], state)
        else:
            qtext = "Sorry, I didn't get that. "
            qtext += process_text(state["qtext"], state)
        
        flush(chat.display, qtext, "call")
        chat.receiving.set(True)
        return
    
    # we don't start these until we know the response works
    
    state["$lm$"] = match
    state["$counter$"] += 1
    
    variable_assignments = state["assign"]
    for varname, value in variable_assignments:
        if varname in KEYWORDS or not isinstance(value, str) or not is_varname(varname):
            print("Bad assignment attempted:", (varname, value))
        elif varname == "$call$":
            if value in ALLOWED_CALLS:
                operation = ALLOWED_CALLS[value]
                new_window = Toplevel(chat.master)
                new_window.grab_set()
                state[varname] = str(operation(new_window))
                chat.master.wait_window(new_window) # blocks until done
            else:
                print("Can't execute:", value)
        else:
            parsetype = re.split(" ", value, maxsplit=1)
            if parsetype[0] == "!bool" and len(parsetype) == 2:
                try:
                    proc_txt = process_bool(parsetype[1], state)
                    state[varname] = proc_txt
                except:
                    print("Ill-typed assignment:", (varname, value))
            elif parsetype[0] == "!num" and len(parsetype) == 2:
                try:
                    proc_txt = process_num(parsetype[1], state)
                    state[varname] = proc_txt
                except:
                    print("Ill-typed assignment:", (varname, value))
            elif varname in state:
                prev = state[varname]
                if isinstance(prev, bool):
                    proc_txt = process_bool(value, state)
                    state[varname] = proc_txt
                elif isinstance(prev, int) or isinstance(prev, float):
                    proc_txt = process_num(value, state)
                    state[varname] = proc_txt
                elif isinstance(prev, str):
                    proc_txt = process_text(value, state)
                    state[varname] = proc_txt
            else:
                proc_txt = process_text(value, state)
                state[varname] = proc_txt
    
    # refresh
    state["assign"] = []
    state["repqtext"] = None
    state["qkey"] = key
    
    if key not in chat.qscript:
        print("Bad key:", key)
        chat.master.destroy()
    elif key == "end":
        chat.master.destroy()
    else:
        state.update(chat.qscript[key])
        
        qtext = process_text(state["qtext"], state)
        flush(chat.display, qtext, "call")
        chat.receiving.set(True)

# only qkey, qtext, allowed, and assign are unreplaceable keywords
# will only return strings
# To expect: nth word of response?
# To expect: trimming for response, stemming for certain words, sentence structure
# Alternatively, make all responses one word

# this method is ideally pure
def process_text(txt, state):
    txt = shallow_process_text(txt, state)
    
    # at this point everything is a string, number, or conditional
    # do arithmetic first, which cannot have nested expressions
    # then do conditionals, which can be nested
    # assume conditionals have only floats/ints or text and other conditionals
    
    fmatch = arithexp_check(txt)
    while fmatch:
        mtext = fmatch.group()[1:-1]
        l, r = fmatch.span()
        try:
            w = str(sp.safe_call(mtext, "num"))
        except:
            print("Bad arithmetic expression in text:", mtext)
            w = "False"   # python thinks this is an int and a bool so yay
        txt = txt[:l] + w + txt[r:]
        
        fmatch = arithexp_check(txt)
    
    fmatch = leaf_conditional_check(txt)
    while fmatch:
        mtext = fmatch.group()[1:-1]
        l, r = fmatch.span()
        guard, rest = re.split(r"[@]", mtext, maxsplit=1)
        try:
            a, b = re.split(r"[|]", rest, maxsplit=1)
            gval = sp.safe_call(guard, "bool")
            if gval:
                txt = txt[:l] + a + txt[r:]
            else:
                txt = txt[:l] + b + txt[r:]
        except (TypeError, SyntaxError):
            options = re.split(r"[|]", rest)
            try:
                opt_index = int(guard)
                if opt_index < len(options):
                    txt = txt[:l] + options[opt_index] + txt[r:]
                else:
                    txt = txt[:l] + options[-1] + txt[r:]
            except ValueError:
                print("Bad guard in text: ", guard)
                txt = txt[:l] + options[-1] + txt[r:]
        
        fmatch = leaf_conditional_check(txt)
    
    ##
    # potentially many more replacements can happen, dates etc.
    
    return txt

def leaf_conditional_check(text):
    return re.search(r"[{][^{}]*?[@][^{}]*?[}]", text)

'''
An arithmetic expression after all variable replacements can only have numbers, spaces, parens, +, -, *, /, %, and decimal points. Just a sanity check, mainly we're looking for the boundary {}.
'''
def arithexp_check(text):
    return re.search(r"[{][^@|{}]*?[}]", text)
    #return re.search(r"[{][0-9.+\-*\s/\(\)%]*?[}]", text)

'''
Find-replace all variable names in the text, while checking that variable names are appropriately formatted.
'''
def shallow_process_text(txt, state):
    for key in state:
        if key not in KEYWORDS and is_varname(key):
            txt = txt.replace(key, str(state[key]))
    
    return txt

def process_bool(txt, state):
    txt = shallow_process_text(txt, state)
    return sp.safe_call(txt, "bool")

def process_num(txt, state):
    txt = shallow_process_text(txt, state)
    return sp.safe_call(txt, "num")

'''
My guess is that outside of ETC_KEY, other future-selection behaviour can be handled at the script level, since we can decompose possibilities

Guards cannot involve higher level dependency.

This is a pure method.
'''
def get_key(options, response, state = {}):
    for resp in options:
        if isinstance(resp, str):
            matching = re.search(resp, response, re.IGNORECASE)
            if matching != None:
                return options[resp], matching.group()
        else:
            reg, guard = resp
            matching = re.search(reg, response, re.IGNORECASE)
            # at this point guard should contain only literals
            try:
                flag = process_bool(guard, state)
                if matching != None and flag:
                    return options[resp], matching.group()
            except:
                print("Bad expression for transition guard:", guard)
    
    return options.get(ETC_KEY), ""

if __name__ == "__main__":
    main(DEFAULT_SCRIPT)
