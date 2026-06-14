from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/list_files")
async def list_files():
    raise HTTPException(
        status_code=403,
        detail="File endpoint disabled before runtime sandbox authorization",
    )

@app.get("/read_file")
async def read_file(filename: str):
    raise HTTPException(
        status_code=403,
        detail="File endpoint disabled before runtime sandbox authorization",
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
