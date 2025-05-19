import uvicorn
import os
os.environ["CPU_DISABLE_ONE_DNN"] = "1"

if __name__ == "__main__":
    uvicorn.run("app.api:app", host="0.0.0.0", port=5001)