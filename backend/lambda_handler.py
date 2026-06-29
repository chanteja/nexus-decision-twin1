# Lambda entrypoint for the API (API Gateway → Mangum → FastAPI).
from mangum import Mangum

from api.app import app

handler = Mangum(app)
