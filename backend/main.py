import os
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

# 强制指向桌面上的指定文件夹
FOLDER_PATH = "/Users/youfeini/Desktop/Zhifei_System/Project_Files"

@app.get("/list_files")
async def list_files():
    # 如果桌面没有这个文件夹，自动创建，避免报错
    if not os.path.exists(FOLDER_PATH):
        os.makedirs(FOLDER_PATH)
    files = os.listdir(FOLDER_PATH)
    return {"files": files}

@app.get("/read_file")
async def read_file(filename: str):
    file_path = os.path.join(FOLDER_PATH, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {"filename": filename, "content": content}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
