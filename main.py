import getopt

from notion.client import NotionClient
from bs4 import BeautifulSoup
from notion.block import *
from tqdm import tqdm
import re
import sys


def parse_note(path):
    print('Note parsing process started...')
    book_note = {
        'notes': []
    }
    soup = BeautifulSoup(open(path), 'lxml')
    result = soup.select('.bodyContainer div')
    is_note = False
    for i in range(len(result)):
        clazz = result[i].get('class')[0]
        text = result[i].get_text(strip=True)
        if clazz == 'bookTitle':
            book_note['title'] = text
        elif clazz == 'authors':
            book_note['authors'] = text
        elif clazz == 'sectionHeading':
            book_note['notes'].append([SubheaderBlock, text])
            book_note['notes'].append([TextBlock, ''])
        elif clazz == 'noteHeading':
            if text.startswith('Highlight'):
                book_note['notes'].append([TextBlock, text, re.findall(r'[(](.*?)[)]', text)[0]])
            else:
                book_note['notes'].append([TextBlock, text])
                is_note = True
        elif clazz == 'noteText':
            if is_note:
                book_note['notes'].append([CalloutBlock, text])
                is_note = False
            else:
                book_note['notes'].append([QuoteBlock, text])
            need_divider = i + 1 < len(result) and not result[i + 1].get_text(strip=True).startswith('Note')
            if need_divider:
                book_note['notes'].append([DividerBlock, ''])
    return book_note


def write_to_notion(token, database_url, book_note):
    print('Note parsing process completed.')
    print('Start writing to notion...')
    client = NotionClient(token_v2=token)
    database = client.get_collection_view(database_url)
    row = database.collection.add_row()
    row.name = book_note['title']
    row.authors = book_note['authors']
    result = database.build_query(search=book_note['title'], sort=[{
        "direction": "descending",
        "property": "Created"
    }]).execute()
    page_id = result[0].id

    page = client.get_block(page_id)
    for child in tqdm(book_note['notes']):
        if child[0] is DividerBlock:
            page.children.add_new(DividerBlock)
        elif child[0] is CalloutBlock:
            page.children.add_new(child[0], title=child[1], icon="💡")
        else:
            if len(child) > 2:
                page.children.add_new(child[0], title=child[1], color=child[2])
            else:
                page.children.add_new(child[0], title=child[1])
    print('Writing process completed.')


def parse_arg():
    token = None
    database_url = None
    file = None
    argv = sys.argv[1:]
    try:
        opts, args = getopt.getopt(argv, 'ht:d:f:')
    except getopt.GetoptError as e:
        print("Input option not recognized!")
        print("python main.py -t <token_v2> -d <database_url> -f <file_path>")
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print("python main.py -t <token_v2> -d <database_url> -f <file_path>")
            sys.exit()
        if opt in ['-t']:
            token = arg
        if opt in ['-d']:
            database_url = arg
        if opt in ['-f']:
            file = arg
    if token is None or database_url is None or file is None:
        print("Missing args!")
        print("python main.py -t <token_v2> -d <database_url> -f <file_path>")
        sys.exit(2)
    return token, database_url, file


def main():
    token, database_url, file = parse_arg()
    # book_note = parse_note('notes.html')
    # print(book_note)
    write_to_notion(token, database_url, parse_note(file))


if __name__ == '__main__':
    main()
