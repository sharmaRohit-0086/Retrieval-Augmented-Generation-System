from fastapi import (FastAPI, UploadFile,
                     HTTPException, Depends, BackgroundTasks)
import os
import shutil
import io
from db import get_db, File, FileChunk
from sqlalchemy.orm import Session
from file_parser import FileParser
from background_tasks import TextProcessor, client
from sqlalchemy import select
from pydantic import BaseModel
import openai
import google.generativeai as genai


app = FastAPI()


class QuestionModel(BaseModel):
    question: str

class AskModel(BaseModel):
    document_id: int
    question: str


@app.get("/")
async def root(db: Session = Depends(get_db)):
    # Query the database for all files
    files_query = select(File)
    files = db.scalars(files_query).all()

    # Format and return the list of files including file_id and filename
    files_list = [{"file_id": file.file_id, "file_name": file.file_name} for file in files]
    return files_list

@app.post("/uploadfile/")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile, db: Session = Depends(get_db)): # noqa
    # Define allowed file extensions
    allowed_extensions = ["txt", "pdf"]

    # Check if the file extension is allowed
    file_extension = file.filename.split('.')[-1]
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="File type not allowed")

    folder = "sources"
    try:
        # Ensure the directory exists
        os.makedirs(folder, exist_ok=True)

        # Secure way to save the file
        file_location = os.path.join(folder, file.filename)

        file_content = await file.read()  # Read file content as bytes

        with open(file_location, "wb+") as file_object:
            # Convert bytes content to a file-like object
            file_like_object = io.BytesIO(file_content)
            # Use shutil.copyfileobj for secure file writing
            shutil.copyfileobj(file_like_object, file_object)

        content_parser = FileParser(file_location)
        file_text_content = content_parser.parse()
        # save file details in the database
        new_file = File(file_name=file.filename,
                        file_content=file_text_content)
        db.add(new_file)
        db.commit()
        db.refresh(new_file)

        # Add background job for processing file content
        background_tasks.add_task(TextProcessor(db, new_file.file_id).chunk_and_embed, file_text_content) # noqa

        return {"info": "File saved", "filename": file.filename}

    except Exception as e:
        # Log the exception (add actual logging in production code)
        print(f"Error saving file: {e}")
        raise HTTPException(status_code=500, detail="Error saving file")


# Function to get similar chunks
async def get_similar_chunks(file_id: int, question: str, db: Session):
    try:
        # Create embeddings for the question (assuming client and embedding creation logic)
        response = client.embeddings.create(input=question, model="text-embedding-ada-002")
        question_embedding = response.data[0].embedding

        similar_chunks_query = select(FileChunk).where(FileChunk.file_id == file_id)\
            .order_by(FileChunk.embedding_vector.l2_distance(question_embedding)).limit(10)
        similar_chunks = db.scalars(similar_chunks_query).all()

        return similar_chunks

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask/")
async def ask_question(request: AskModel, db: Session = Depends(get_db)):
    """
    # Using OpenAI (I don't have free API Key)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    openai.api_key = OPENAI_API_KEY

    if OPENAI_API_KEY is None:
        raise HTTPException(status_code=500, detail="OpenAI API key is not set")

    try:
        similar_chunks = await get_similar_chunks(request.document_id, request.question, db)
        
        # Construct context from the similar chunks' texts
        context_texts = [chunk.chunk_text for chunk in similar_chunks]
        context = " ".join(context_texts)

        # Update the system message with the context
        system_message = f"You are a helpful assistant. Here is the context to use to reply to questions: {context}"

        # Make the OpenAI API call with the updated context
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": request.question},
            ]
        )

        return {"response": response.choices[0].message.content}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    """

    GOOGLE_API_KEY = os.getenv("OPENAI_API_KEY")
    genai.configure(api_key=GOOGLE_API_KEY)

    if GOOGLE_API_KEY is None:
        raise HTTPException(status_code=500, detail="GOOGLE API key is not set")

    try:
        similar_chunks = await get_similar_chunks(request.document_id, request.question, db)
        
        # Construct context from the similar chunks' texts
        context_texts = [chunk.chunk_text for chunk in similar_chunks]
        context = " ".join(context_texts)

        # Update the system message with the context
        system_message = f"You are a helpful assistant. Here is the context to use to reply to questions: {context}"

        # Make the OpenAI API call with the updated context
        escaped = context.replace("'", "").replace('"', "").replace("\n", " ")
        prompt = ("""You are a helpful and informative bot that answers questions using text from the reference passage included below. \
        Be sure to respond in a complete sentence, being comprehensive, including all relevant background information. \
        However, you are talking to a non-technical audience, so be sure to break down complicated concepts and \
        strike a friendly and converstional tone. \
        If the passage is irrelevant to the answer, you may ignore it.
        QUESTION: '{query}'
        PASSAGE: '{relevant_passage}'
        ANSWER:""").format(query=request.question, relevant_passage=escaped)

        model = genai.GenerativeModel('gemini-pro')
        answer = model.generate_content(prompt)

        return {"response": answer.text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/find-similar-chunks/{file_id}")
async def find_similar_chunks_endpoint(file_id: int, question_data: QuestionModel, db: Session = Depends(get_db)):
    try:
        similar_chunks = await get_similar_chunks(file_id, question_data.question, db)

        # Format the response
        formatted_response = [
            {"chunk_id": chunk.chunk_id, "chunk_text": chunk.chunk_text}
            for chunk in similar_chunks
        ]

        return formatted_response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))