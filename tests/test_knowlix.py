def test_import_knowlix(): 
    import knowlix
    assert knowlix is not None

def test_cli_import():
    from knowlix import cli
    assert cli is not None

def test_cli_main():
    from knowlix.cli import main
    assert callable(main)