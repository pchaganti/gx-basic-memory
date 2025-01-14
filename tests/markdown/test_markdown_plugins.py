"""Tests for markdown-it plugins."""

import pytest
from markdown_it import MarkdownIt

from basic_memory.markdown.plugins import observation_plugin, relation_plugin


def test_observation_plugin():
    """Test observation plugin parsing."""
    md = MarkdownIt().use(observation_plugin)
    
    # Basic observation
    tokens = md.parse("- [design] Core feature #important #mvp")
    obs_token = next(t for t in tokens if t.meta and 'observation' in t.meta)
    obs = obs_token.meta['observation']
    
    assert obs['category'] == 'design'
    assert obs['content'] == 'Core feature'
    assert set(obs['tags']) == {'important', 'mvp'}
    assert obs['context'] is None
    
    # With context
    tokens = md.parse("- [feature] Authentication system #security (Required for MVP)")
    obs_token = next(t for t in tokens if t.meta and 'observation' in t.meta)
    obs = obs_token.meta['observation']
    
    assert obs['category'] == 'feature'
    assert obs['content'] == 'Authentication system'
    assert set(obs['tags']) == {'security'}
    assert obs['context'] == 'Required for MVP'
    
    # Without category
    tokens = md.parse("- Authentication system #security (Required for MVP)")
    obs_token = next(t for t in tokens if t.meta and 'observation' in t.meta)
    obs = obs_token.meta['observation']
    
    assert obs['category'] is None
    assert obs['content'] == 'Authentication system'
    assert set(obs['tags']) == {'security'}
    assert obs['context'] == 'Required for MVP'


def test_observation_edge_cases():
    """Test observation plugin edge cases."""
    md = MarkdownIt().use(observation_plugin)
    
    # Multiple word tags
    tokens = md.parse("- [tech] Database #high-priority #needs-review")
    obs_token = next(t for t in tokens if t.meta and 'observation' in t.meta)
    obs = obs_token.meta['observation']
    assert set(obs['tags']) == {'high-priority', 'needs-review'}
    
    # Multiple word category
    tokens = md.parse("- [user experience] Design #ux")
    obs_token = next(t for t in tokens if t.meta and 'observation' in t.meta)
    obs = obs_token.meta['observation']
    assert obs['category'] == 'user experience'
    
    # Parentheses in content
    tokens = md.parse("- [code] Function (x) returns y #function")
    obs_token = next(t for t in tokens if t.meta and 'observation' in t.meta)
    obs = obs_token.meta['observation']
    assert obs['content'] == 'Function (x) returns y'
    assert obs['context'] is None
    
    # Multiple hashtags together
    tokens = md.parse("- [test] Feature #important#urgent#now")
    obs_token = next(t for t in tokens if t.meta and 'observation' in t.meta)
    obs = obs_token.meta['observation']
    assert set(obs['tags']) == {'important', 'urgent', 'now'}


def test_relation_plugin():
    """Test relation plugin parsing."""
    md = MarkdownIt().use(relation_plugin)
    
    # Basic relation
    tokens = md.parse("- implements [[Auth Service]]")
    rel_token = next(t for t in tokens if t.meta and 'relations' in t.meta)
    rel = rel_token.meta['relations'][0]
    
    assert rel['type'] == 'implements'
    assert rel['target'] == 'Auth Service'
    assert rel['context'] is None
    
    # With context
    tokens = md.parse("- depends_on [[Database]] (Required for persistence)")
    rel_token = next(t for t in tokens if t.meta and 'relations' in t.meta)
    rel = rel_token.meta['relations'][0]
    
    assert rel['type'] == 'depends_on'
    assert rel['target'] == 'Database'
    assert rel['context'] == 'Required for persistence'


def test_relation_edge_cases():
    """Test relation plugin edge cases."""
    md = MarkdownIt().use(relation_plugin)
    
    # Multiple word type
    tokens = md.parse("- is used by [[Client App]] (Primary consumer)")
    rel_token = next(t for t in tokens if t.meta and 'relations' in t.meta)
    rel = rel_token.meta['relations'][0]
    assert rel['type'] == 'is used by'
    
    # Extra spaces
    tokens = md.parse("-   specifies   [[Format]]   (Documentation)")
    rel_token = next(t for t in tokens if t.meta and 'relations' in t.meta)
    rel = rel_token.meta['relations'][0]
    assert rel['type'] == 'specifies'
    assert rel['target'] == 'Format'


def test_inline_relations():
    """Test finding relations in regular content."""
    md = MarkdownIt().use(relation_plugin)
    
    # Single inline link
    tokens = md.parse("This references [[Another Doc]].")
    rel_token = next(t for t in tokens if t.meta and 'relations' in t.meta)
    rel = rel_token.meta['relations'][0]
    assert rel['type'] == 'links to'
    assert rel['target'] == 'Another Doc'
    
    # Multiple inline links
    tokens = md.parse("Links to [[Doc1]] and [[Doc2]].")
    rel_token = next(t for t in tokens if t.meta and 'relations' in t.meta)
    rels = rel_token.meta['relations']
    assert len(rels) == 2
    assert {r['target'] for r in rels} == {'Doc1', 'Doc2'}


def test_combined_plugins():
    """Test both plugins working together."""
    md = (MarkdownIt()
          .use(observation_plugin)
          .use(relation_plugin))
    
    content = """# Document

Some text with a [[Link]].

## Observations
- [tech] Implements [[Feature]] #important
- [design] References [[AnotherDoc]] (For context)
"""
    
    tokens = md.parse(content)
    
    # Should find both observations and relations
    observations = [t.meta['observation'] for t in tokens if t.meta and 'observation' in t.meta]
    relations = [r for t in tokens if t.meta and 'relations' in t.meta for r in t.meta['relations']]
    
    assert len(observations) == 2
    assert any(o['category'] == 'tech' and 'important' in o['tags'] for o in observations)
    assert any(o['category'] == 'design' and o['context'] == 'For context' for o in observations)
    
    # Should find all relations (Feature, AnotherDoc, and Link)
    assert len(relations) == 3
    assert any(r['target'] == 'Link' and r['type'] == 'links to' for r in relations)
    assert any(r['target'] == 'Feature' for r in relations)
    assert any(r['target'] == 'AnotherDoc' for r in relations)