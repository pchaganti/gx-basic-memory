"""Test to explore markdown-it token structure."""
from textwrap import dedent
from markdown_it import MarkdownIt

def test_token_structure():
    """Analyze markdown-it token structure."""
    content = dedent('''
    # Title

    ## Observations
    - [test] First line #tag
    - [another] Second line #tag2
    ''')

    md = MarkdownIt()
    tokens = md.parse(content)

    # Print full token structure
    print("\nToken structure:")
    for i, token in enumerate(tokens):
        attrs = {key: getattr(token, key) for key in dir(token) 
                if not key.startswith('_') and not callable(getattr(token, key))}
        print(f"\nToken {i}:")
        for key, value in attrs.items():
            print(f"  {key}: {value!r}")
