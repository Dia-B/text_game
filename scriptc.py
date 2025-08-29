import re
import safe_parser as sp

TRANSITION_SEP = r"->"
ASSIGN_SEP = r"<-"
NEXT_INST = r"\n    "
REPQMARKER = r"#"

VARNAME_REGEX = r"[$][a-zA-Z]\w*?[$]"
TAG_REGEX = r"\w+"

ETC_KEY = r"[^\S\s]"

BLOCK_REGEX = r"^"+TAG_REGEX+"\n(?:[ ]{4}.+\n)+\n"

KEYWORDS = ["qkey", "assign", "repqtext", "qtext", "allowed"]

def is_valid_tag(txt):
    return re.search(r"^"+TAG_REGEX + r"$", txt) != None

def is_varname(txt):
    return re.search(r"^"+VARNAME_REGEX + r"$", txt) != None

def is_callable_expression(txt, t):
    ls = re.findall(VARNAME_REGEX, txt)
    for match in ls:
        txt = txt.replace(match, "False")
    return sp.safe_test(txt, t)

def is_regex(txt):
    try:
        re.findall(txt, "")
        is_valid = True
    except re.error:
        is_valid = False
    return is_valid

def get_guard(st):
    if st == "REST":
        return ETC_KEY
    
    # note that guard will have no quotes (else exception)
    # hence greedily seeking the last quote gives the regex
    has_guard = re.search(r"^[\"].*[\"], ", st)
    if has_guard:
        l, r = has_guard.span()
        guard = st[r:]
        if not is_callable_expression(guard, "bool"):
            raise Exception("Badly formatted guard.", guard)
        regex = has_guard.group()[1:-3]
        if not is_regex(regex):
            raise Exception("Badly formatted regex.", regex)
        return (regex, guard)
    is_reg = re.search(r"^[\"].*[\"]$", st)
    if is_reg:
        regex = st[1:-1]
        if not is_regex(regex):
            raise Exception("Badly formatted regex.", regex)
        return regex
    raise Exception("Badly formatted transition instruction.", st)

def parse_file(filename):
    with open(filename, encoding="utf-8") as f:
        read_data = f.read()
    return parse_str(read_data)

def parse_str(data_string):
    blocks = re.findall(BLOCK_REGEX, data_string, re.MULTILINE)
    
    qscript = {
        "start":{"qtext":"No start defined.","allowed":{ETC_KEY:"end"}},
        "end":{"qtext":"", "allowed":{}}
    }
    
    for block in blocks:
        vals = [s.strip() for s in re.split(NEXT_INST, block)]
        qkey = vals[0]
        qtext = vals[1]
        assign = []
        allowed = {}
        repqtext = None
        for val in vals[2:]:
            if val[0] == REPQMARKER:
                repqtext = val[1:].strip()
                continue
            attempt1 = re.split(TRANSITION_SEP, val, maxsplit=1)
            if len(attempt1) == 2:
                keyguard, tag = attempt1
                keyguard = keyguard.strip()
                tag = tag.strip()
                if not is_valid_tag(tag):
                    raise Exception("Invalid tag.", tag)
                allowed[get_guard(keyguard)] = tag
                continue
            attempt2 = re.split(ASSIGN_SEP, val, maxsplit=1)
            if len(attempt2) == 2:
                varname, toset = attempt2
                varname = varname.strip()
                toset = toset.strip()
                if not is_varname(varname):
                    raise Exception("Bad varname.", varname)
                
                # assign statements internally always look like text
                assign.append((varname, toset))
                continue
        qscript[qkey] = {
            "qtext": qtext,
            "allowed": allowed
        }
        if repqtext != None:
            qscript[qkey]["repqtext"] = repqtext
        if assign != []:
            qscript[qkey]["assign"] = assign
    
    return qscript




'''
General format

qscript["shortname"] = {
    "qtext": "Replaceable question text?",
    "allowed":
        {("regex", "guard"):"othershortname",
        "regex":"newshortname",
        ...
        ETC_KEY:"absorbingshortname"},
    "assign":[("varname", value)]
    "repqtext": "Qtext if bad response"
}

ETC_KEY:None or not defining ETC_KEY makes the question repeat on failure. "repqtext" and "assign" are optional.

allowed keys may be matched with regexes, qtext and keys will not be
qtext will be find-replaced for local information

the flow goes like
key -> qtext -> allowedkey (from user) -> key

more explictly
key -> question -> user input -> regex prefix match to allowedkey -> new key

Known bindings:
$response$ - response
$counter$ - question counter
$lm$ - last match
$call$ - stores result of function calls (when you assign with call it calls the script)

{expr@a|b} is the syntax for conditionals
{evaluable} is the syntax for arithmetic expressions, which can only compute with floats or ints
'''

