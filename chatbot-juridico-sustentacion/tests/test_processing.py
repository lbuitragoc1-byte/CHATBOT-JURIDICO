from app.processing import chunk_text, extract_entities

def test_chunks():
    assert len(chunk_text('palabra '*300,100,20)) > 1

def test_entities():
    entities = extract_entities('Ley 1581 de 2012 y artículo 15')
    assert 'Ley 1581 de 2012' in entities['Normas']
