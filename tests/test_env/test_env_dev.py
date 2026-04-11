from knowlix.settings import settings

def test_dev_env():
    assert settings.ENV == "dev"
    assert "dev" in settings.PG_DATABASE_URL
    assert "dev" in settings.LLM_API_KEY
