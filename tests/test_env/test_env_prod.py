from knowlix.settings import settings

def test_prod_env():
    assert settings.ENV == "prod"
    assert "prod" in settings.PG_DATABASE_URL
    assert "prod" in settings.LLM_API_KEY
