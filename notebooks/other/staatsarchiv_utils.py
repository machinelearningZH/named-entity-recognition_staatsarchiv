import re
import spacy


def generic_text_cleaning(d):
    """
    Clean various quirks and superfluous characters and sequences.
    Improve text quality e.g. by rejoining hyphenated words.
    """

    # Strip whitespace from beginning and end of text.
    d = d.strip()

    # Remove various escape sequences (line breaks, tabs etc.).
    d = re.sub(r"[\n\r\t\b\f]+", " ", d)

    # Remove hyphenation.
    d = re.sub(r"(?<=[a-zäüö])-(?=[a-zäöü])", "", d)

    # Rejoin hyphenated words that go over two lines.
    # Identify words separated by a hyphen and two spaces
    # then remove the hyphen and the spaces.
    d = re.sub(r"(\w+-  \w+)", lambda x: x.group().replace("-  ", ""), d)

    # Remove single characters followed by a punctuation mark.
    d = re.sub(r"(?<=\s).\.(?=\s)", " ", d)

    # Remove roman numerals.
    d = re.sub(
        r"(?<=\s)(I.|II.|III.|IV.|V.|VI.|VII.|VIII.|IX.|X.|XI.|XII.|XIII.|XIV.|XV.)(?=\s)",
        " ",
        d,
    )

    # Remove non breaking spaces and other escape sequences.
    escape_sequences = r"(\x04|\x1a|\xa0|\x00|\ue83a|\x19|\uf06c|\x10|\x17|\x13|\x11|<space>|\x16|\x18|\x1b|\x15)"
    pattern = re.compile(escape_sequences)
    d = re.sub(pattern, " ", d)

    # Remove several superfluous characters. (Note Adrian: Parentheses removed from regex)
    d = re.sub(r"(\[|\])", "", d)
    d = re.sub(
        r"[«»\/\"\‘\[\]“„`'{}⎬⊥∑ø|#*⎭⎫¨™†№±）︵□╯┻ ━ಠ¬___\^><_\*ϭйϵϯºϱϴϮ]", " ", d
    )
    d = re.sub(r" – ", " ", d)

    # Replace several symbolic chars with actual word.
    d = re.sub(r"&", " und ", d)
    d = re.sub(r"§", " Paragraph ", d)
    d = re.sub(r"=", " gleich ", d)

    # Remove editorial remark.
    d = re.sub(r" sic! ", " ", d)
    # «recte:» indicates an editorial correction which follows directly after.
    d = re.sub(r"recte:", "", d)
    d = re.sub(r"Grafik:", " ", d)
    d = re.sub(r"Grafik", " ", d)

    # Remove single characters.
    d = re.sub(r"\s.(?=\s)", " ", d)

    # Remove  "-.-"".
    d = re.sub("(?<=\s)-\.-(?=\s)", "", d)

    # Replace multiple spaces with single space.
    d = re.sub(r"[\s]+", " ", d)

    # Again strip whitespace after all cleaning operations.
    d = d.strip()

    return d


def get_spacy_stopwords():
    """
    Get stopwords from spacy language model for German.
    Combine with additional stopwords from spacy and sort.
    """

    nlp = spacy.load("de_core_news_lg")

    # Get default stopwords.
    stopwords_model = nlp.Defaults.stop_words

    # Get more stopwords and combine to final list.
    stopwords_defaults = list(spacy.lang.de.stop_words.STOP_WORDS)
    stopwords = list(stopwords_model) + stopwords_defaults
    stopwords = sorted(list(set(stopwords)))
    del nlp

    return stopwords


date_mapping_gszh = {
    "1883": "1883-01-01",
    "1879-09": "1879-09-01",
    "1813": "1813-01-01",
    "1883-11": "1883-11-01",
    "1879": "1879-01-01",
    "1879-07": "1879-07-01",
    "1888-04": "1888-04-01",
    "1888": "1888-01-01",
    "1829": "1829-01-01",
    "1820-05": "1820-05-01",
    "1814": "1814-01-01",
    "1803": "1803-01-01",
}
