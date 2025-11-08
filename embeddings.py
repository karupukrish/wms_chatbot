import os
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import CSVLoader, PyPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from config import VECTOR_DIR, DATA_DIR, CSV_FILE

def build_vectorstore():
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    if os.path.exists(VECTOR_DIR):
        try:
            print("✅ Loading existing vectorstore...")
            return FAISS.load_local(VECTOR_DIR, embeddings, allow_dangerous_deserialization=True)
        except Exception as e:
            print(f"⚠️ Could not load existing vectorstore: {e}")

    print("🔨 Building new vectorstore...")
    docs = []
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

    if os.path.exists(CSV_FILE):
        try:
            print(f"📂 Loading CSV: {CSV_FILE}")
            loader = CSVLoader(CSV_FILE)
            docs.extend(loader.load())
        except Exception as e:
            print(f"⚠️ CSV load error: {e}")

    if os.path.exists(DATA_DIR):
        for f in os.listdir(DATA_DIR):
            if f.lower().endswith(".pdf"):
                pdf_path = os.path.join(DATA_DIR, f)
                try:
                    print(f"📄 Loading PDF: {pdf_path}")
                    loader = PyPDFLoader(pdf_path)
                    docs.extend(loader.load_and_split())
                except Exception as e:
                    print(f"⚠️ Skipping PDF {f}: {e}")

    if not docs:
        print("⚠️ No documents found — running in DB-only mode.")
        return None

    texts = text_splitter.split_documents(docs)
    vectorstore = FAISS.from_documents(texts, embeddings)
    vectorstore.save_local(VECTOR_DIR)
    print(f"✅ Vectorstore built with {len(texts)} chunks!")
    return vectorstore

vectorstore = build_vectorstore()
