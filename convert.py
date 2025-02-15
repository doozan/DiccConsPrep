#!/usr/bin/python3
#
# Copyright (c) 2025 Jeff Doozan
#
# This is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re
import sys

ALL_POS = {
    "N": "n",
    "V": "v",
    "Adj": "adj",
    "Adv": "adv",
}

def parse_pos(text):
    return [ALL_POS[p.strip(".")] for p in text.split("/")]

def parse_headline(text):

    m = re.match(r"[*]+(.*)\s((?:(?:V|N|Adj|Adv)[.]?/?)+\.)\s*(.*)", text)

    word = m.group(1)
    pos = parse_pos(m.group(2))
    sense = m.group(3)

    # strip numbering
    word = re.sub("[1-9]$", "", word)
    word = re.sub(r"[1-9]\s*\(se\)$", "(se)", word)
    word = re.sub(r"[1-9]\s*se$", "se", word)

    if pos == ["v"]:
        word = word.replace("r(se)", "rse")

    assert word.replace(" ", "").isalpha(), [word, text]

    if sense:
        assert (sense.startswith("(") and sense.endswith(")"))
        sense = sense[1:-1]

    return word, pos, sense



# preps mentioned in the prologue
PREPS = ["a", "a través de", "acerca de", "alrededor de", "ante", "bajo", "cerca de", "como", "con", "contra", "de", "dentro de", "desde", "detrás de", "durante", "en", "en torno a", "entre", "frente a", "hacia", "hasta", "para", "para con", "por", "respecto", "según", "sin", "sobre", "tras", "AC", "DAT", "GER"]
# not mentioned and / forms
PREPS = PREPS + ["conforme a", "en cuanto a", "a / de", "a / DAT", "de / en", "de / a"]

# sort longest to shortest to ensure regex matches "a través de" before "a"
ITEMS = "|".join(sorted(PREPS, key=lambda x: (len(x)*-1, x)))
SENSE_RE = fr"·\s*({ITEMS})\s+(.*)"

def parse_prep(text, word_sense):

    assert text.startswith("·"), text

    splits = re.split(r"([♦◊])", text)
    text = splits.pop(0)

    notes = []
    while(splits):
        note_type = splits.pop(0)
        note_text = splits.pop(0).strip()
        notes.append((note_type, note_text))

    assert "◊" not in text
    assert "♦" not in text

    m = re.match(SENSE_RE, text)
    if not m:
        return

    prep = m.group(1)
    extra = m.group(2)

    assert "DAT" not in extra, text

    if extra.startswith("("):
        sense, extra = re.match(r"\((.*?)\)\s*(.*)", extra).groups()
    else:
        sense = None

    if not sense:
        sense = word_sense

    examples = [e.strip() for e in extra.split("|") if e.strip()]

    if examples:
        assert all(e for e in examples), text
    else:
        assert notes and all(n for n in notes)

    return {
        "prep": prep,
        "sense": sense,
        "ex": examples,
        "usage": [note_text for note_type, note_text in notes]
    }


def parse_see_also(text):

    targets = []

    prev_pos = None
    for item in text.split(", "):
        m = re.match(r"(?:Véase[:]? )?\[(.+?)\] (.*)", item)
        if m:
            pos, target = m.groups()
        else:
            if prev_pos:
                pos, target = prev_pos, item
            else:
                raise ValueError("unhandled line", text)

        assert "[" not in pos and "[" not in target

        targets.append(f"{target} ({pos})")
        prev_pos = pos

    return "; ".join(targets)


def parse_word(lines):
    global prev_lemma

    assert len(lines) > 1, lines

    lemma, pos, word_sense = parse_headline(lines[0])

    if "adj" in pos:
        assert pos[0] == "adj"

    word = {
        "lemma": lemma,
        "pos": pos,
        "usage": [],
        "preps": [],
    }

    full_lines = []
    split_line = []
    for line in lines[1:]:
        if any(line.startswith(p) for p in ["→", "·", "♦", "◊"]):
            if split_line:
                full_lines.append(" ".join(split_line))
                split_line = []

        split_line.append(line)
    if split_line:
        full_lines.append(" ".join(split_line))

    see_also = None
    for line in full_lines:
        if line.startswith("·"):
            word["preps"].append(parse_prep(line, word_sense))

        if line.startswith("→"):
            assert line == full_lines[-1]
            target = parse_see_also(line[1:].strip())
            word["usage"].append(f"véase tambíen {target}")

        elif line.startswith("♦"):
            word["usage"].append(line[1:].strip())

        elif line.startswith("◊"):
            word["usage"].append(line[1:].strip())

    return word

# Manual cleanup for badly formatted lines
LINE_FIXES = {
    '*casi a quemarropa. | Martín me acribillaba a preguntas más o menos impertinentes.': ['casi a quemarropa. | Martín me acribillaba a preguntas más o menos impertinentes.'],
    '*encadenamiento con el pasado que no te deja avanzar.': ['encadenamiento con el pasado que no te deja avanzar.'],

    '*alistamiento (integración)': ['*alistamiento N. (integración)'],
    '*comarca del Almanzora, podemos ver este fenómeno.': ['comarca del Almanzora, podemos ver este fenómeno.'],
    '*contrición ante las recriminaciones del mundo artístico. | El presidente mostraba anoche por': ['contrición ante las recriminaciones del mundo artístico. | El presidente mostraba anoche por'],
    '*al Gobierno.': ['al Gobierno.'],
    '*inquietar(se) (intranquilidad)': ['*inquietar(se) V. (intranquilidad)'],
    '*de Borges es el carácter primordiamente literario de todos sus secretos, es el poseso de': ['de Borges es el carácter primordiamente literario de todos sus secretos, es el poseso de'],

    '*compensar(se) V. (compensación) meter': ['*compensar(se) V. (compensación)'],
    '*filtración N. edar': ['*filtración N.'],

    '· acerca De momento se ha lanzado una fase beta, gratuita, con la que la compañía quiere': ['· acerca de De momento se ha lanzado una fase beta, gratuita, con la que la compañía quiere'],
    '· acerca El primer paso es realizar un sondeo acerca de los conocimientos del alumno.': ['· acerca de El primer paso es realizar un sondeo acerca de los conocimientos del alumno.'],

    'manifestado su contento del resultado obtenido': ["manifestado su contento del resultado obtenido."],
    'oposición le critica no haber sabido ilusionar a los ciudadanos': ['oposición le critica no haber sabido ilusionar a los ciudadanos.'],

    'conjunto. engarzar(se) V. (relación, sujeción)': ['conjunto.','*engarzar(se) V. (relación, sujeción)'],

    'discrepancia en cuanto a la lengua, el procedimiento se tramitará en castellano': ['discrepancia en cuanto a la lengua, el procedimiento se tramitará en castellano.'],
    'respecto a una nueva financiación autonómica': ['respecto a una nueva financiación autonómica.'],
    '· respecto Se divulgó la idea de que el libro era muy duro respecto a ciertos personajes': ['· respecto Se divulgó la idea de que el libro era muy duro respecto a ciertos personajes.'],
    'que deban estar resueltos en tan escaso tiempo': ['que deban estar resueltos en tan escaso tiempo.'],
    'sociedad esclavista': ['sociedad esclavista.'],
    'lentitud para su desalojo | Otro de los problemas que parecía tener esta técnica es la lentitud': ['lentitud para su desalojo. | Otro de los problemas que parecía tener esta técnica es la lentitud'],
    'respecto a sus finanzas en los últimos años': ['respecto a sus finanzas en los últimos años.'],

    'recochinearse V. (burla)': ['*recochinearse V. (burla)'],
    'resolución N.': ['*resolución N.'],

    "con el nuevo Código Penal. ‘": ["con el nuevo Código Penal."],
    "· con Desde el punto de vista de la demanda no existe sustituibilidad con otros servicios": ["· con Desde el punto de vista de la demanda no existe sustituibilidad con otros servicios."],
    "Francia a Portugal": ["Francia a Portugal."],

    "contacto. → [V.] desidentificar(se)": ["contacto.", "→ [V.] desidentificar(se)"],

    "→ Véase: suscribir(se)": ["→ [V.] suscribir(se)"],
    "→ Véase: trasplante": ["→ [N.] trasplante"],
    "→ Véase: transmisible": ["→ [Adj.] transmisible"],
    "→ Véase: transmutar(se)": ["→ [V.] transmutar(se)"],

    "→ [N.] amor, desamor [V.] enamorar(se)": ["→ [N.] amor, desamor, [V.] enamorar(se)"],
    "→ [N.] lazo, vínculo [V.] entrelazar": ["→ [N.] lazo, vínculo, [V.] entrelazar"],
    "→ [N.] rotura, ruptura [V.] irrumpir": ["→ [N.] rotura, ruptura, [V.] irrumpir"],

    "*doblegarse(se) V. (sumisión)": ["*doblegar(se) V. (sumisión)"],

    "· en Aquellos días en los que la soledad y el frío se amalgaban en una misma sustancia.": ["· en Aquellos días en los que la soledad y el frío se amalgamaban en una misma sustancia."],
    "anterioridad de al menos 11 días respecto a la fecha de su emisión.": ["antelación de al menos 11 días respecto a la fecha de su emisión."],
    "· por El ministro de Economía estalló y mostró su colera por el atrevimiento del Banco de": ["· por El ministro de Economía estalló y mostró su cólera por el atrevimiento del Banco de"],
    "· con (conflicto) Es un tipo conflictivo: en Valencia se lió a bofetadas con el entonces presidente.": ["· con (conflicto) Es un tipo conflictivo: en Valencia se lio a bofetadas con el entonces presidente."],
    "· con (pareja) En Jerez me lié con la actriz joven que hacía de madre de la actriz vieja.": ["· con (pareja) En Jerez me lie con la actriz joven que hacía de madre de la actriz vieja."],
    "· para De aquí pasa a intentar demostrar que no hay predestinacion para el infiemo.": ["· para De aquí pasa a intentar demostrar que no hay predestinación para el infierno."],
    "· de La tasa de crecimiento que se utiliza para la prognosís de población se calcula teniendo": ["· de La tasa de crecimiento que se utiliza para la prognosis de población se calcula teniendo"],
    "· a La adopción del ancho de vía europeo homogeneíza nuestra red a la de nuestros futuros": ["· a La adopción del ancho de vía europeo homogeneiza nuestra red a la de nuestros futuros"],
    "· en El vulcanismo moderno se enraiza en los primeros tiempos de la Tierra. | La economía": ["· en El vulcanismo moderno se enraíza en los primeros tiempos de la Tierra. | La economía"],
    "ética enraiza en Canarias. | Esta cultura de tolerancia e incluso exaltación del consumo": ["ética enraíza en Canarias. | Esta cultura de tolerancia e incluso exaltación del consumo"],
    "· por (división) Lo que cobraba por actuacion lo dividia por la cantidad de músicos de la": ["· por (división) Lo que cobraba por actuacion lo dividía por la cantidad de músicos de la"],
}


def print_word(word, prev_word, json=False):

    if json:
        # strip empty values before printing
        preps = [{k:v for k,v in sense.items() if v} for sense in word["preps"]]
        w = {k:v for k,v in word.items() if v}
        w["preps"] = preps
        print(str(w) + ",")
        return

    if not prev_word or prev_word["lemma"] != word["lemma"]:
        print("_____")
        print(word["lemma"])

    def print_kv(k, v, depth):
        if not v:
            return

        pad = "  " * depth
        if isinstance(v, list):
            for _v in v:
                print(f"{pad}{k}: {_v}")
        else:
            print(f"{pad}{k}: {v}")

    print_kv("pos", "; ".join(word["pos"]), 0)

    for k in ["meta", "usage"]:
        v = word.get(k)
        print_kv(k, v, 1)

    for prep in word["preps"]:
        gloss = prep["prep"] if not prep["sense"] else prep["prep"] + " (" + prep["sense"] + ")"
        print_kv("gloss", gloss, 1)
        for k in ["ex", "usage"]:
            v = prep.get(k)
            print_kv(k, v, 2)

def main():

    import argparse

    parser = argparse.ArgumentParser(description="Convert dictionary to machine readable format")
    parser.add_argument("--json", help="dump as json", action='store_true')
    parser.add_argument("filename", help="txt extracted from pdf")
    args = parser.parse_args()

    if args.json:
        print("[")

    word_lines = []
    skip_intro=True
    prev_word = None
    with open(args.filename) as infile:
        for line in infile:
            line = line.strip()
            if skip_intro:
                if line.startswith("Utrecht, marzo de 2020"):
                    skip_intro=False
                continue

            for line in LINE_FIXES.get(line, [line]):

                # skip blank lines and letter titles
                if len(line) <= 1:
                    continue

                if line.startswith("*"):
                    if word_lines:
                        word = parse_word(word_lines)
                        print_word(word, prev_word, args.json)
                        prev_word = word
                        word_lines = []

                word_lines.append(line)

    if word_lines:
        word = parse_word(word_lines)
        print_word(word, prev_word, args.json)

    if args.json:
        print("]")

if __name__ == "__main__":
    main()
