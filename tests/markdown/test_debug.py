"""Debug markdown-it token structure."""

from markdown_it import MarkdownIt
from basic_memory.markdown.plugins import observation_plugin, parse_observation, is_observation

def test_debug_observations():
    """Debug observation parsing."""
    md = MarkdownIt().use(observation_plugin)
    
    content = "- [design] Core feature #important #mvp"
    tokens = md.parse(content)
    
    # Print token info
    print("\nTokens:")
    for i, token in enumerate(tokens):
        print(f"\nToken {i}:")
        print(f"  Type: {token.type}")
        print(f"  Tag: {token.tag}")
        print(f"  Content: {token.content}")
        print(f"  Nesting: {token.nesting}")
        if hasattr(token, 'meta'):
            print(f"  Meta: {token.meta}")
            
    # Try the functions directly
    token = next(t for t in tokens if t.type == 'inline')
    print("\nTesting observation functions:")
    print(f"Is observation: {is_observation(token)}")
    obs = parse_observation(token)
    print(f"Parsed observation: {obs}")
    
    # Verify meta was set
    print("\nVerifying meta:")
    token = next(t for t in tokens if t.meta and 'observation' in t.meta)
    print(f"Meta observation: {token.meta}")
