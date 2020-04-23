import os
import bs4
import regex
import shutil
import pickle
from collections import Counter


def main():

    off = "\t"

    TXT_DIR = "theatregratuit-txt"
    fnames, n_files = get_fnames(TXT_DIR)

    # save trimmed files to dir
    TRIM_DIR = "trimmed"
    check_create_dir(TRIM_DIR)

    # formatting
    FORM_DIR = "formatted"

    # remainder
    REST_DIR = "rest"
    check_create_dir(REST_DIR, clean=True)

    DUMP = ".DATA.pkl"

    # if process already done, just load the files
    if not os.path.isfile(DUMP):
        DATA = get_all_data(fnames, n_files, TXT_DIR, TRIM_DIR)
        with open(DUMP, "wb") as o:
            pickle.dump(DATA, o, pickle.HIGHEST_PROTOCOL)
        print(f"saving cached trimmed data as {DUMP}")
    else:
        print(f"loading cached trimmed data from {DUMP}")
        with open(DUMP, "rb") as f:
            DATA = pickle.load(f)
    separator_print()

    FUMP = ".FORMATTED.pkl"

    markers_to_lines_threshold = 0.2

    # if process already done, just load the files
    if not os.path.isfile(FUMP):

        check_create_dir(FORM_DIR, clean=True)

        # limit = 50
        for i, (f, data) in enumerate(DATA.items()):
            # if i > limit: break
            # if f != "count-2975020-LES_PHENICIENNES.txt": continue
            print(f"{i+1:4}/{n_files} | attempting formatting of: {TRIM_DIR}/{f}")
            data = add_formatting_upper(data)
        separator_print()
        underprint(f"first pass done: files with characters in caps")

        # counting markers: result of the first pass
        for f, data in DATA.items():
            data = add_double_markers_count(data)

        n_unf = 0
        for i, (f, data) in enumerate(DATA.items()):
            if data["markers_to_lines_ratio"] > markers_to_lines_threshold:
                save_lines(f, data["formatted"], le_dir=FORM_DIR)
            else:
                n_unf += 1
        print(
            f"found {n_files - n_unf} files above {markers_to_lines_threshold} markers to lines ratio, saved to: {FORM_DIR}/{f}"
        )
        separator_print()

        with open(FUMP, "wb") as o:
            pickle.dump(
                {f: {
                    "formatted": d["formatted"],
                    "markers_count": d["markers_count"],
                    "markers_to_lines_ratio" : d["markers_to_lines_ratio"]
                } for f, d in DATA.items()}, o, pickle.HIGHEST_PROTOCOL
            )
        underprint(f"saving formatted data as {FUMP}")
    else:
        print(f"loading cached formatted data from {FUMP}")
        n_unf = 0
        with open(FUMP, "rb") as f:
            pkl = pickle.load(f)
            for fname, d in pkl.items():
                DATA[fname]["formatted"] = d["formatted"]
                DATA[fname]["markers_count"] = d["markers_count"]
                DATA[fname]["markers_to_lines_ratio"] = d["markers_to_lines_ratio"]
                if d["markers_to_lines_ratio"] < markers_to_lines_threshold:
                    n_unf += 1

    i = 0
    for f, data in DATA.items():
        if data["markers_to_lines_ratio"] < markers_to_lines_threshold:
            i += 1
            print(
                f"{i:4}/{n_unf} | below {markers_to_lines_threshold} markers to lines ratio, processing & saving to: {REST_DIR}/{f}"
            )
            data = add_character_counter(data)
            data = add_formatting_lower(data)
            save_lines(f, data["char_formatted"], le_dir=REST_DIR)

    separator_print()
    print(f"saved {n_files - n_unf} formatted files to {FORM_DIR}/")
    print(f"saved {n_unf} char formatted files to {REST_DIR}/")
    separator_print()

    DS_DIR = "theatregratuit-dataset"
    if not os.path.isdir(DS_DIR):
        os.mkdir(DS_DIR, clean=True)

    underprint(f"saving a copy of all files to {DS_DIR}")
    for f, _ in DATA.items():
        if os.path.isfile(os.path.join(FORM_DIR, f)):
            shutil.copyfile(os.path.join(FORM_DIR, f), os.path.join(DS_DIR, f))
        if os.path.isfile(os.path.join(REST_DIR, f)):
            shutil.copyfile(os.path.join(REST_DIR, f), os.path.join(DS_DIR, f))

# ----------------------------------------
# splitting & other corpus utils


def add_character_counter(data, threshold=1):
    lines = data["formatted"]
    C = Counter()
    for i, l in enumerate(lines):
        # init char including L'/M. and short dash, until the first punctuation mark
        char_re = regex.match(R["char_init_dot_dash_colon"], l)
        if char_re:
            C[char_re.group(1).strip()] += 1
    # no empty dicts
    if C:
        # only dicts with at least one repeated el will be valid
        only_ones = True
        for el in C:
            if C[el] > 1:
                only_ones = False
                break

        if not only_ones:
            # https://stackoverflow.com/a/15862021
            data["char_counter"] = Counter(
                el for el in C.elements() if C[el] >= threshold
            )

    return data


def add_double_markers_count(data):
    lines = data["formatted"]
    n = 0
    for (l, m) in zip(lines[:-1], lines[1:]):
        if "<|e|>" in l and "<|s|>" in m:
            n += 1
    data["markers_count"] = n
    data["markers_to_lines_ratio"] = n / data["trimmed_len"]
    return data


def save_split_groups(
    pattern,
    data_dict,
    le_dir,
    threshold=1,
    le_dir_with="with",
    le_dir_without="without",
    verbose=True,
):
    check_create_dir(le_dir_with, clean=True)
    check_create_dir(le_dir_without, clean=True)
    with_it, without = split_by_regex(
        data_dict, pattern, threshold=threshold, verbose=verbose
    )
    separator_print()
    print(f"pattern: {pattern}")
    print(f"threshold: {threshold}")
    print(f"{len(with_it):4} files with pattern saved to {le_dir_with}/")
    print(f"{len(without):4} files without pattern saved to {le_dir_without}/")
    for i, f in enumerate(with_it):
        shutil.copyfile(os.path.join(le_dir, f), os.path.join(le_dir_with, f))
    for i, f in enumerate(without):
        shutil.copyfile(os.path.join(le_dir, f), os.path.join(le_dir_without, f))


def split_by_regex(data_dict, pattern, threshold=1, verbose=True):
    with_pattern = []
    without_pattern = []
    if verbose:
        underprint(f"splitting data: is there {threshold} occurrences of {pattern}?")
    total = len(data_dict.keys())
    for i, (fname, data) in enumerate(data_dict.items()):
        if verbose:
            print(f"{i+1:4}/{total} | searching in {fname}")
        found = 0
        for l in data["trimmed"]:
            if regex.search(pattern, l):
                found += 1
                if found == threshold:
                    break
        if found == threshold:
            with_pattern.append(fname)
        else:
            without_pattern.append(fname)
    return with_pattern, without_pattern


def matches_to_lines_ratio(data, pattern, verbose=False):
    f = data["fname"]
    lines = data["trimmed"]
    lines_len = data["trimmed_len"]
    n_matches = 0
    for l in lines:
        n_matches += len(regex.findall(pattern, l))
    r = n_matches / lines_len
    if verbose:
        print(
            f"ratio: {r:.2f} | n_matches: {n_matches:4} for {lines_len:4} lines | {f}"
        )
    return r


# ----------------------------------------
# FORMATTING
# ----------------------------------------

# ------------------------------------------------------------------------
# LEAN MINORITY: No caps


def add_formatting_lower(data):

    if "char_counter" not in data:
        data["char_formatted"] = data["formatted"]
        return data

    char_formatted = []  # add the initial marker

    # skip first match, so that entire start of text caught in one extract
    # (adding <|s|> at the very top of file after the loop)
    skipped = False

    for i, l in enumerate(data["formatted"]):
        found_char = False
        for (char, cnt) in reversed(data["char_counter"].most_common()):
            if found_char:
                break
            char_re = regex.match(char + "\\b", l)
            if char_re:
                found_char = True
                end_cr = char_re.span()[1]
                start = l[:end_cr]
                rest = l[end_cr:]

                # is the rest just empty / only punct
                if regex.match(R["trailing_punct"], rest):
                    char_formatted, skipped = append_markers(
                        char_formatted, skipped, test_for_markers=True
                    )
                    char_formatted.append(start.upper() + ".")
                    break

                # check for dot'n'dash
                brk, char_formatted, skipped = word_init_append_splits(
                    char_formatted,
                    R["[.,] —"],
                    l,
                    rest,
                    skipped,
                    end_cr,
                    "search",
                    test_for_markers=True,
                    capitalize_start=True
                )
                if brk:
                    break

                # check for :
                brk, char_formatted, skipped = word_init_append_splits(
                    char_formatted,
                    R[":"],
                    l,
                    rest,
                    skipped,
                    end_cr,
                    "search",
                    test_for_markers=True,
                    capitalize_start=True
                )
                if brk:
                    break

                # is there a parenthesis

                # # is there a comma then didasc
                # if regex.match(R[","], rest):
                #     pass

        if not found_char:
            char_formatted.append(l)

    # save lines
    data["char_formatted"] = char_formatted

    # print_lines(char_formatted)

    return data


# ------------------------------------------------------------------------
# FAT MAJORITY: CAPS


def add_formatting_upper(data):

    formatted = ["<|s|>"]

    # skip first match, so that entire start of text caught in one extract
    # (adding <|s|> at the very top of file after the loop)
    skipped = False

    for j, l in enumerate(data["trimmed"]):

        # cleanup various typos
        l = fix_line(l)

        # ------------------------------------------------------------------------
        # preemptively: no full caps words, no : or —: append straight away

        if (
            not regex.search(R["WORD"], l)
            and not regex.search(R[":"], l)
            and not regex.search(R["—"], l)
        ):
            formatted.append(l)
            continue

        # ------------------------------------------------------------------------
        # check for full caps line (and check previous line as well, as often
        # there are several full caps lines in a row and we only want the first
        if l.isupper():  # and not regex.match(R["LINE"], formatted[-1]):
            formatted, skipped = append_markers(formatted, skipped)
            l = regex.sub(R["trailing_punct"], "", l) + "."
            formatted.append(l)
            continue

        # slightly more elaborate pattern for full caps line
        caps_line = regex.match(R["LINE"], l)
        if caps_line:  # and not regex.match(R["LINE"], formatted[-1]):
            formatted, skipped = append_markers(formatted, skipped)
            l = regex.sub(R["trailing_punct"], "", l) + "."
            formatted.append(l)
            continue

        # ------------------------------------------------------------------------
        # init capital letters word
        word_init = regex.match(R["WORD_INIT"], l)
        # check that previous line is not already with full caps
        if word_init:

            end_wi = word_init.span()[1]
            rest = l[end_wi:]

            # print_test(l, l[:end_wi], rest)

            # is there a dot'n'dash straight away?
            cont, formatted, skipped = word_init_append_splits(
                formatted, R["[.,] —"], l, rest, skipped, end_wi
            )
            if cont:
                continue

            # is there a colon straight away?
            cont, formatted, skipped = word_init_append_splits(
                formatted, R[":"], l, rest, skipped, end_wi
            )
            if cont:
                continue

            # is there a paren straight away?
            paren = regex.match(R["(.*)"], rest)
            if paren:
                end_paren = paren.span()[1]

                # print_test(l, l[:end_wi+end_paren], l[end_wi+end_paren:])

                # is there a dot'n'dash after that?
                cont, formatted, skipped = word_init_append_splits(
                    formatted, R["[.,] —"], l, rest, skipped, end_wi, "search"
                )
                if cont:
                    continue

                # check for :
                cont, formatted, skipped = word_init_append_splits(
                    formatted, R[":"], l, rest, skipped, end_wi, "search"
                )
                if cont:
                    continue

                formatted, skipped = append_markers(formatted, skipped)
                formatted.append(l[: end_wi + end_paren] + ".")
                formatted.append(l[end_wi + end_paren :].strip())
                continue

            # print_test(l, l[:end_wi], rest)

            # get all caps words on the line, and check the last one,
            # find the last one (https://stackoverflow.com/a/2988680)
            more_caps_words = regex.finditer(R["WORD"], l)
            last_caps_word = None
            for last_caps_word in more_caps_words:
                pass
            if last_caps_word:

                # print_test(l, rest, last_caps_word.group(0))

                end_lcw = last_caps_word.span()[1]
                rest = l[end_lcw:]

                if rest:

                    # print_test(l, l[:end_lcw], rest)

                    # check for colon
                    cont, formatted, skipped = word_init_append_splits(
                        formatted, R[":"], l, rest, skipped, end_lcw,
                    )
                    if cont:
                        more_caps_words, last_caps_word = None, None  # needs reset
                        continue

                    # check for opt dot/comma and dash
                    cont, formatted, skipped = word_init_append_splits(
                        formatted, R["[.,] —"], l, rest, skipped, end_lcw,
                    )
                    if cont:
                        more_caps_words, last_caps_word = None, None  # needs reset
                        continue

                    # check for parenthesis

                    # check for didascalia: find colon later
                    cont, formatted, skipped = word_init_append_splits(
                        formatted, R[":"], l, rest, skipped, end_lcw, "search",
                    )
                    if cont:
                        more_caps_words, last_caps_word = None, None  # needs reset
                        continue

                    # check for didascalia: find either dot or dot'n'dash later
                    cont, formatted, skipped = word_init_append_splits(
                        formatted, R[".( —)?"], l, rest, skipped, end_lcw, "search",
                    )
                    if cont:
                        more_caps_words, last_caps_word = None, None  # needs reset
                        continue

                # nothing after several caps chars
                else:
                    formatted, skipped = append_markers(formatted, skipped)
                    formatted.append(l[:end_lcw] + ".")
                    more_caps_words, last_caps_word = None, None  # needs reset
                    continue

            more_caps_words, last_caps_word = None, None  # needs reset

            # is there a comma ?
            if regex.match(R[","], rest):

                full_stop = regex.search(R["."], rest)
                if full_stop:
                    end_fs = full_stop.span()[1]
                    # if there's something beyond the ".", split there
                    if rest[end_fs:]:
                        # print_test(l, l[:end_wi], rest[:end_fs], rest[end_fs:])
                        # find full stop later
                        cont, formatted, skipped = word_init_append_splits(
                            formatted, R["."], l, rest, skipped, end_wi, "search"
                        )
                        if cont:
                            continue

                formatted, skipped = append_markers(formatted, skipped)
                formatted.append(l)
                continue

            # print_test(l, l[:end_wi], rest)

            # finally, simply append
            formatted, skipped = append_markers(formatted, skipped)
            formatted.append(l[:end_wi] + ".")
            formatted = check_append(formatted, rest.strip())
            continue

        # otherwise just append the line
        formatted.append(l)

    # add very end markers, trim lines
    formatted = markers_final_cleanup(formatted)

    # save lines
    data["formatted"] = formatted

    # print_lines(formatted)

    return data


def lc_append_splits(formatted, reg, l, skipped):
    # search for delimiters, e.g. ". —" or ":"
    reg_re = regex.search(reg, l)
    if reg_re:
        formatted, skipped = append_markers(formatted, skipped)
        start = l[: reg_re.span()[0]] + "."
        formatted.append(start)
        formatted = check_append(formatted, l[reg_re.span()[1] :].strip())
        return True, formatted, skipped
    else:
        return False, formatted, skipped


def word_init_append_splits(
    formatted, reg, l, rest, skipped, end_char, attr="match",
    test_for_markers=False, capitalize_start=False
):
    reg_re = getattr(regex, attr)(reg, rest)
    if reg_re:
        formatted, skipped = append_markers(
            formatted, skipped, test_for_markers=test_for_markers
        )
        start = l[:end_char]
        if capitalize_start:
            start = start.upper()
        # end of prefix just after didascalia, before boundary punctuation
        if (attr == "search"):
            start += l[end_char : end_char + reg_re.span()[0]]
        start += "."
        formatted.append(start)
        formatted = check_append(formatted, rest[reg_re.span()[1] :].strip())
        return True, formatted, skipped
    else:
        return False, formatted, skipped


def append_markers(lines, skipped, test_for_markers=False):
    """will append markers, and turn skipped to true"""
    if test_for_markers:
        if (
            skipped
            and not regex.search(R["LINE"], lines[-1])
            and lines[-2:] != ["<|e|>", "<|s|>"]
        ):
            lines.append("<|e|>")
            lines.append("<|s|>")
    else:
        if skipped and not regex.search(R["LINE"], lines[-1]):
            lines.append("<|e|>")
            lines.append("<|s|>")
    return lines, True


def check_append(lines, bit):
    if bit:
        lines.append(bit)
    return lines


def markers_final_cleanup(lines):
    lines = remove_trailing_lines(lines)
    lines.append("<|e|>")
    return lines


def remove_trailing_lines(lines):
    if regex.match(R["blank_line"], lines[-1]):
        for i, l in enumerate(reversed(lines)):
            if not regex.match(R["blank_line"], l):
                return lines[:-i]
    else:
        return lines


def fix_line(l):

    # remove footnote calls (digit)
    l = regex.sub(R["(footnote)"], "", l)
    # fix space within certain words
    l = regex.sub(R["sc_ene"], r"\1\2", l)
    l = regex.sub(R["lenglu_me"], r"\1\2", l)
    l = regex.sub(R["ch_oeur"], r"\1\2", l)
    l = regex.sub(R["deuxi_eme"], r"\1\2", l)
    # multiple non breaking space --> one
    l = regex.sub(R["non_breaking_space"], " ", l)
    return l


# ---------------------------------------
# Les Regices


def make_regices():
    return {
        "blank_line": regex.compile("^\s*$"),
        "blank_line_with_rubbish": regex.compile("^[\p{Z}\p{P}]*$"),
        "trailing_punct": regex.compile("[\p{Z}\p{P}]*$"),
        # -----------------------------
        # trim beginning & end of files
        # -----------------------------
        "character": regex.compile(
            "^((les\p{Z}*)?pe*rsonna *ge|"
            + "(les\p{Z}*)?acteurs|"
            + "dramatis personae|"
            + "avertissement|"
            + "entreparleur|"
            + "biographies|"
            + "apparences|"
            + "personrage|"
            + "persongueules|"
            + "pépersonâge)",
            regex.IGNORECASE,
        ),
        "author": regex.compile("^de$", regex.IGNORECASE),
        "additional_author": regex.compile(
            "^(\(Auteur inconnu\)|"
            + "Voltaire|"
            + "de\s+Georges Courteline|"
            + "Translation en prose de Jean Sibil|"
            + "Anton Pavlovitch Tchekhov|"
            + "EUGENE LABICHE, A. LEFRANC et MARC-MICHEL|"
            + "Alexandre Hardy)$"
        ),
        "la_scene": regex.compile("^La scène"),
        "fin": regex.compile("(fin|rideau|f1n|inachev|manque)", regex.IGNORECASE),
        # -----------------------------
        # the meaty part: formatting
        # -----------------------------
        # search for lines made of full caps + punct/space, as well as some
        # very common words listing characters, and didascalia in ()
        "WORD": regex.compile("\\b\p{Lu}{2,}\\b"),
        "LINE": regex.compile(
            "^((\p{Lu}+|"
            + "seule?|"
            + "puis( tout le monde)?|"
            + "moins|"
            + "et)[\p{Z}\p{P}]*)+\p{Z}*"
            + "(\(.*?\))*\p{Z}*$"
        ),
        "(line)": regex.compile("^\(.*\)$"),
        # a caps word (dash ok), + optional M./L' etc.
        "WORD_INIT": regex.compile("^(?:\p{Lu}[.']\p{Z}*)*[\p{Lu}\p{Pd}]{2,}\\b"),
        "init_char_sep": regex.compile(
            "^((?:\p{Lu}[.']\p{Z}*)?([\p{L}\-]+))\p{Z}*([,.]\p{Z}*[–—]\p{Z}*|:\p{Z}*)"
        ),
        "char_dot_dash": regex.compile(
            "^(?:\p{Lu}[.']\p{Z}*)?([\p{L}\p{Pd}\p{Z}]+)\p{Z}*[,.]*\p{Z}*[–—]+\p{Z}*$"
        ),
        "[.,] —": regex.compile("\p{Z}*[,.]*\p{Z}*-?[—–]+\p{Z}*"),
        ".( —)?": regex.compile("\p{Z}*\.\p{Z}*\p{Pd}*\p{Z}*"),
        ":": regex.compile("\p{Z}*:\p{Z}*"),
        ".": regex.compile("\p{Z}*\.\p{Z}*"),
        ",": regex.compile("\p{Z}*,\p{Z}*"),
        "—": regex.compile("\p{Z}*[—–]\p{Z}*"),
        "(.*)": regex.compile("\p{Z}*\(.*?\)"),
        # single file with "A. or B. as characters: count-3202657-De_la_liberte.txt"
        "LETTER_CHARS": regex.compile("^(\p{Lu}\.)\p{Z}\p{Pd}\p{Z}"),
        # ----------------------------
        # regices for innards cleaning
        # ----------------------------
        # initial L'/M. etc, letters & space, : or — at the end
        "char_colon_or_dash": regex.compile(
            "^((?:\p{Lu}[.']\p{Z}*)?" + "[\p{L}\p{Pd}\p{Z}]+)" + "\p{Z}[:—]\p{Z}"
        ),
        # initial L'/M. etc, letters & space, a parenthesis, : or — at the end
        "char_colon_or_dash_paren": regex.compile(
            "^((?:\p{Lu}[.']\p{Z}*)?"
            + "[\p{L}\p{Pd}\p{Z}]+)"
            + "(\p{Z}\(.*?\))"
            + "\p{Z}[:—]\p{Z}"
        ),
        # lower case character, optionally with didasc, ending in dot and dash,
        "char_lc_dot_dash": regex.compile(
            "^([\p{Ll}\p{Z}]+)" + "(([,\p{Z}].*?)*)" + "\.\p{Z}*\p{Pd}\p{Z}*"
        ),
        "char_init_dot_dash_colon": regex.compile(
            r"^((?:\p{Lu}[.']\p{Z}*)?[\p{L}\p{Z}\-']+)\p{Z}*(:|[.,]\p{Z}*[–—])"
        ),
        # ----------------------------
        # line cleanup
        # ----------------------------
        "(footnote)": regex.compile("\(\d+\)"),
        "non_breaking_space": regex.compile(" {2,}"),  # non-breaking space
        "sc_ene": regex.compile("(SC)\p{Z}+([EÈ]NE)", regex.IGNORECASE),
        "lenglu_me": regex.compile("(LENGLUM)\p{Z}+([ÉE])", regex.IGNORECASE),
        "ch_oeur": regex.compile("(CH)\p{Z}+(ŒUR)", regex.IGNORECASE),
        "deuxi_eme": regex.compile("(DEUXI)\p{Z}+(ÈME)", regex.IGNORECASE),
    }


def index_of_regex_match(lines, r, trim=True):
    lines_len = len(lines)
    ind = 0
    found = False
    for i, l in enumerate(lines):
        if found:
            break
        if regex.search(r, l):
            found = True
            k = 1
            if trim:
                while i + k < lines_len and regex.match(R["blank_line"], lines[i + k]):
                    k += 1
            ind = i + k
            break
    return ind


# ----------------------------------------
# data pipelines


def get_all_data(fnames, n_files, txt_dir, trim_dir):
    D = {}
    for i, f in enumerate(fnames):
        print(f"{i+1:4}/{n_files} | trimming & writing: {txt_dir}/{f}")
        D[f] = get_data(f, le_dir=txt_dir)
        save_lines(f, D[f]["trimmed"], le_dir=trim_dir)
    separator_print()
    underprint(f"finished loading from {txt_dir} & trimming saved to {trim_dir}/")
    return D


def get_data(f, le_dir, trim=True, trim_dir="trimmed"):
    raw, lines, lines_len = get_lines(f, le_dir=le_dir)
    data = {
        "fname": f,
        "raw": raw,
        "lines": lines,
        "lines_len": lines_len,
    }
    if trim:
        trimmed, indices = trim_lines(f, lines, lines_len)
        trimmed_len = len(trimmed)
        data.update({"trimmed": trimmed, "trimmed_len": trimmed_len})
        data.update(indices)
    else:
        _, trimmed, trimmed_len = get_lines(f, le_dir=trim_dir)
        data.update({"trimmed": trimmed, "trimmed_len": trimmed_len})
    return data


def trim_lines(fname, lines, lines_len):
    author_index = find_author(fname, lines, lines_len)
    if not author_index:
        author_index = index_of_regex_match(lines, R["additional_author"])
    char_index = find_characters(fname, lines, lines_len)
    end_index = find_end(fname, lines, lines_len)
    start_index = max(author_index, char_index)
    return (
        lines[start_index:end_index],
        {
            "char_index": char_index,
            "author_index": author_index,
            "end_index": end_index,
            "start_index": start_index,
        },
    )


# ----------------------------------------
# trimming character, author, end


def find_characters(fname, lines, lines_len):
    feydeau = False  # almost all Feydeau files have 2-3 blocks of char
    vega = False  # Vega files can be cut up to line "La scène..."

    char_index = 0
    found_char = False
    limit = 15

    if fname in (
        "count-3109664-SYLVANIRE.txt" "count-3397657-LA_VEINE.txt",
        "count-1712853-LE_VERITABLE_SAINT_GENEST.txt",
        "count-1537913-LES_ESPAGNOLS_EN_DANEMARK.txt",
        "count-3263112-LA_MORT_DE_WALLENSTEIN.txt",
        "count-2267304-LAmour_medecin.txt",
        "count-2037607-LHabit_vert.txt",
        "count-2158361-ANDROMEDE.txt",
        "count-2675834-Cromwell.txt",
        "count-2047890-LE_ROI.txt",
        "count-3031455-Nono.txt",
    ):
        feydeau = True

    # have a long prologue
    if fname in ("count-1355612-UNE_FEMME_EST_UN_DIABLE.txt"):
        limit = 27

    for j, l in enumerate(lines[:limit]):
        if found_char:
            break
        if "Feydeau" in l and fname not in (
            "count-2316496-On_va_faire_la_cocotte.txt",
            "count-2199212-Les_Paves_de_lours.txt",
        ):
            feydeau = True
        if "Lope de Vega" in l:
            vega = True
        if regex.match(R["character"], l):
            found_char = True
            k = 1
            # files with space after char > k + 1
            if fname in (
                "count-1037209-LES_MAMELLES_DE_TIRESIAS_-_Guillaume_Apollinaire.txt",
                "count-958980-Le_gendre_de_Monsieur_Poirier_-_Emile_Augier.txt",
                "count-1072543-CornPR.txt" "count-2158361-ANDROMEDE.txt",
                "count-1182649-LE_MONDE_OU_L.txt",
                "count-2037607-LHabit_vert.txt",
                "count-1072543-CornPR.txt",
            ):
                k += 1
            # more annoying exceptions
            if fname in ("count-959005-LOrphelin_de_la_Chine_-_Voltaire.txt",):
                # find init caps words only, no space (lest we go to the end)
                while j + k < lines_len and regex.match(R["WORD"], lines[j + k]):
                    k += 1
            elif vega:
                # all vega can go up to "La scène"
                while j + k < lines_len and not regex.match(
                    R["la_scene"], lines[j + k]
                ):
                    k += 1
            else:
                k = end_of_block_and_trim(lines, lines_len, j, k)
                # annoying exceptions: more chars after blank line
                if feydeau:
                    k = end_of_block_and_trim(lines, lines_len, j, k)
                    # some files like Feydeau with three !
                    if fname in (
                        "count-1537913-LES_ESPAGNOLS_EN_DANEMARK.txt",
                        "count-3263112-LA_MORT_DE_WALLENSTEIN.txt",
                        "count-2267304-LAmour_medecin.txt",
                        "count-3397657-LA_VEINE.txt",
                    ):
                        k = end_of_block_and_trim(lines, lines_len, j, k)
                    if fname == "count-2675834-Cromwell.txt":
                        k = end_of_block_and_trim(lines, lines_len, j, k)
                        k = end_of_block_and_trim(lines, lines_len, j, k)
            char_index = j + k
    return char_index


def end_of_block_and_trim(lines, lines_len, j, k):
    # find end of block
    while j + k < lines_len and not regex.match(R["blank_line"], lines[j + k]):
        k += 1
    # trim empty lines
    while j + k < lines_len and regex.match(R["blank_line"], lines[j + k]):
        k += 1
    return k


def find_author(fname, lines, lines_len):
    author_index = 0
    found_author = False
    for j, l in enumerate(lines[:10]):
        if found_author:
            break
        if regex.match(R["author"], lines[j]):
            found_author = True
            # annoying exceptions
            if fname in (
                "count-1049195-Arret_36_de_lautobus_40_-_Jean_Sibil.txt",
                "count-1396213-Roberto_Succo.txt",
            ):
                k = 1
            elif fname == "count-1541294-Olaf_loriginal.txt":
                k = 2
            else:
                k = 2  # we assume "de\n\nauthor"
                while j + k < lines_len and not regex.match(
                    R["blank_line"], lines[j + k]
                ):
                    k += 1
            author_index = j + k + 1
    return author_index


def find_end(fname, lines, lines_len):
    end_index = lines_len - 1
    found_end = False
    for j, l in enumerate(reversed(lines[-4:])):
        if found_end:
            break
        if regex.search(R["fin"], l):
            found_end = True
            end_index = end_index - j - 1
    return end_index


# ----------------------------------------
# printing


def print_test(*args, utf=False, off="\t"):
    for i, arg in enumerate(args):
        if utf:
            arg_utf8 = arg.encode("utf-8")
        if "\n" in arg:
            print(f"{off}{i}  {arg}", end="")
            if utf:
                print(f"{off}{i}  {arg_utf8}")
        else:
            print(f"{off}{i}  {arg}")
            if utf:
                print(f"{off}{i}  {arg_utf8}")
    print(off + "-" * 40)
    print()


def print_file_stats(fname, i, n_files, char_index, author_index, end_index):
    print(f"file:     {fname}")
    print(f"no:       {i}/{n_files}")
    print(f"end char: {char_index}")
    print(f"end auth: {author_index}")
    print(f"end:      {end_index}")
    print()


def print_lines(lines):
    print("\n".join(lines))


def separator_print(offset=None, blank=False):
    sep = "-" * 40
    if offset:
        sep = offset + sep
    print(sep)
    if blank:
        print()


def underprint(x):
    print(x)
    print("-" * len(x))


# ----------------------------------------
# files


def save_lines(f, lines, le_dir, clean=False):
    check_create_dir(le_dir, clean=clean)
    with open(os.path.join(le_dir, f), "w") as o:
        o.write("\n".join(lines))


def get_lines(input_name, le_dir):
    with open(
        os.path.join(le_dir, input_name), "r", encoding="utf-8", errors="ignore"
    ) as f:
        raw = f.read()
        lines = [l.strip() for l in raw.split("\n")]
    return raw, lines, len(lines)


def get_fnames(le_dir):
    if os.path.isdir(le_dir):
        fnames = [
            x for x in os.listdir(le_dir) if ".txt" == os.path.splitext(x)[-1]
        ]  # don't load vim *.swp files
        n_files = len(fnames)
        print(f"found {n_files} files in directory: {le_dir}")
        separator_print()
        return fnames, n_files
    else:
        print(f"{le_dir} directory not found.")


def check_create_dir(d, clean=False):
    if not os.path.isdir(d):
        os.mkdir(d)
    if clean:
        [os.remove(os.path.join(d, f)) for f in os.listdir(d)]


# ----------------------------------------
# other utils


def binary_insert(lst, el):
    if not lst:
        return [el]
    half = len(lst) // 2
    lo = lst[:half]
    hi = lst[half:]
    if el[1] > hi[0][1]:
        if len(hi) > 1:
            hi = binary_insert(hi, el)
        else:
            return hi + [el]
    elif lo and el[1] < lo[-1][1]:
        lo = binary_insert(lo, el)
    else:
        return lo + [el] + hi
    return lo + hi


if __name__ == "__main__":

    R = make_regices()

    try:
        main()
    except KeyboardInterrupt:
        print("keyboard interrupt")
