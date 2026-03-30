from services.payments import charge_payment, issue_refund


class FastAPI:
    def post(self, path: str):
        def decorator(func):
            return func

        return decorator

    def get(self, path: str):
        def decorator(func):
            return func

        return decorator


app = FastAPI()


@app.post("/payments/charge")
async def charge_endpoint():
    return await charge_payment()


@app.post("/payments/refund")
async def refund_endpoint():
    return await issue_refund()


@app.get("/health")
async def health_check():
    return {"ok": True}
