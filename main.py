from fastapi import FastAPI, UploadFile, File
from app.csv_parser import parse_csv
from app.calculator import calculate_metrics

app = FastAPI(title="Marketplace Profit SaaS MVP")


@app.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    df = await parse_csv(file)
    result = calculate_metrics(df)
    return result
