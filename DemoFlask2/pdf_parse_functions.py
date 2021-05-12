from operator import itemgetter
import fitz
import spacy
from collections import Counter
import re


'''
 To get spicy models, run in console:
 python -m spacy download en_core_web_sm
'''


def pdf_parser(filepath:str):
    doc = fitz.open(filepath)
    font_styles = get_fonts(doc)
    font_meanings = interpret_fonts(font_styles)
    contents = parse_contents(doc,font_meanings, font_styles)
    paragraphs = get_paragraphs_with_titles(contents)
    return paragraphs

def get_fonts(doc):
    """Extracts fonts and their usage in PDF documents.
    :param doc: PDF document to iterate through
    :type doc: <class 'fitz.fitz.Document'>
    :param granularity: also use 'font', 'flags' and 'color' to discriminate text
    :type granularity: bool
    :rtype: [(font_size, count), (font_size, count}], dict
    :return: most used fonts sorted by count, font style information
    """
    font_styles = {}
    for page in doc:
        blocks = page.getText("dict")["blocks"]
        for b in blocks:  # iterate through the text blocks
            if b['type'] == 0:  # block contains text
                for l in b["lines"]:  # iterate through the text lines
                    for s in l["spans"]:  # iterate through the text spans
                        identifier = get_identifier(s)
                        if identifier in font_styles:
                            font_styles[identifier]['count'] = font_styles[identifier]['count'] + 1  # count the fonts usage
                        else:    
                            font_styles[identifier] = {'size': int(s['size']), 'flags': s['flags'], 'font': s['font'],
                                                      'color': s['color'],'count': 1}

    if len(font_styles) < 1:
        raise ValueError("Zero discriminating fonts found!")

    return font_styles

def interpret_fonts(font_styles):
    counts = {}
    sizes = {}
    for font in font_styles:
        counts[font] = font_styles[font]['count']
        sizes[font] = font_styles[font]['size']

    count_sorted = sorted(counts.items(), key=itemgetter(1), reverse=True) 
    size_sorted = sorted(sizes.items(), key=itemgetter(1), reverse=True)

    font_meanings = {}
    normal_font_id = count_sorted[0][0]
    heading_nr = -1
    for nr, style in enumerate(size_sorted[1:]):
        if nr==0 : 
            meaning = 'title'
        # all the fonts bigger than normal are interpreted as headings
        elif font_styles[style[0]]['size'] > font_styles[normal_font_id]['size']:
            meaning = 'heading'+str(nr)
        else:
            meaning = 'other'
        font_meanings[style[0]] = meaning

    font_meanings[normal_font_id] = 'normal'

    return font_meanings

def parse_contents(doc, font_meanings, font_styles):

    doc_contents = [{'label':""}]

    for page in doc:
        blocks = page.getText("dict")["blocks"]
        for b in blocks:  # iterate through the text blocks
            if b['type'] == 0:  # block contains text
                for l in b["lines"]:  # iterate through the text lines
                    for s in l["spans"]:  # iterate through the text spans
                        identifier = get_identifier(s)
                        if identifier in font_meanings:
                            span_meaning = font_meanings[identifier]
                            if doc_contents[-1]['label'] == span_meaning:
                                doc_contents[-1]['text'] = doc_contents[-1]['text'] + s['text']
                            else:
                                if s['text'] != ' ':
                                    doc_contents.append({'label':span_meaning,'text':s['text'],'page':page})
                        else:
                            pass

    return doc_contents[1:]

def get_paragraphs_with_titles(doc_contents):
    paragraphs = []
    for ind, item in enumerate(doc_contents[:-1]):
        this_is_heading = item['label'][:7] == 'heading'
        is_not_toc = not this_is_heading or item['text'].find('Table of Contents')==-1
        is_not_acronyms = not this_is_heading or item['text'].find('Acronyms')==-1
        next_is_normal = doc_contents[ind+1]['label'] == 'normal'
        if this_is_heading and next_is_normal and is_not_toc and is_not_acronyms:
            paragraphs.append({
                'heading' : doc_contents[ind]['text'],
                'text' : doc_contents[ind+1]['text']
            })
    for ind, para in enumerate(paragraphs):                         
        cleantext = re.sub(' +', ' ', para['text'])
        paragraphs[ind]['text'] = cleantext
    return paragraphs

def get_identifier(span):
    span['size'] = round(span['size'],3)
    id_str = "{0}_{1}_{2}_{3}".format(span['size'], span['flags'], span['font'], span['color'])
    return id_str


def get_paragraphs_with_key_words(paragraphs,key_words):
    
    if isinstance(key_words,str):
        key_words = (key_words,)
    nlp = spacy.load('en_core_web_sm')
    paragraphs_with_key_words = []
    for p in paragraphs:
        doc = nlp(p['heading']+p['text'])
        doc_words = [token.lemma_ for token in doc if not token.is_stop]
        key_word_occurrence = [doc_words.count(word) for word in key_words]
        if any([k > 0 for k in key_word_occurrence]):
            p['key_words_info'] = {'key_words':key_words,'counts':key_word_occurrence}
            p['importance'] = sum(key_word_occurrence)
            paragraphs_with_key_words.append(p)

    # sort according to importance
    paragraphs_with_key_words.sort(key=lambda para: para['importance'], reverse=True)

    return paragraphs_with_key_words


