import pandas as pd
from io import StringIO


async def parse_csv(file):
    content = await file.read()
    decoded = content.decode("utf-8")
    df = pd.read_csv(StringIO(decoded))
    return df
