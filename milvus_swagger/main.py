import typer
from typing_extensions import Annotated

from typing import List
from langchain_core.documents import Document
from markdownify import markdownify
from rich import print
import uuid
import os


from langchain_ollama.embeddings import OllamaEmbeddings
from langchain_openai.embeddings import OpenAIEmbeddings
from pymilvus import MilvusClient

from .utils.summarizer import endpoint_summary_chain
from .utils.milvus_db import seutp_milvus_vectorstore, ingest_swagger
from .utils.swagger import get_swagger, resolve_swagger

app = typer.Typer()

@app.command()
def create_database(
    swagger_url: Annotated[str, typer.Argument(help="Swagger URL to fetch the OpenAPI spec from")],
    milvus_uri: Annotated[str, typer.Option(help="Milvus host i.e. http://localhost:19530")],
    db_name: Annotated[str, typer.Option(help="Milvus database name")],
    ollama_embeddings_model: Annotated[str, typer.Option(help="To use Ollama embeddings, specify the model name, which must be installed in the Ollama CLI, see https://ollama.com/blog/embedding-models for more info.")] = None,
    openai_embeddings_model: Annotated[str, typer.Option(help="To use OpenAI embeddings, specify the model name, which must be installed in the OpenAI CLI, see https://platform.openai.com/docs/models for more info.")] = None,
    resume_from_checkpoint_file: Annotated[str, typer.Option(help="Path to the checkpoint file to resume from")] = None,
): 
    """
    Creates a Milvus Vector database from a Swagger URL.
    This command fetches the OpenAPI specification from the provided Swagger URL,
    resolves any references, and ingests the specification into a Milvus vector database.
    """
 
    milvus_db_name = db_name
    # Setup Milvus vectorstore
    if not milvus_uri:
        raise ValueError("Milvus URI is required.")
    
    try:
        client = MilvusClient(
            uri=milvus_uri,
            token="root:Milvus"
        )
    except Exception as e:
        raise ValueError(f"Failed to connect to Milvus: {e}")
    

    if milvus_db_name:
        if milvus_db_name in client.list_databases():
            client.use_database(milvus_db_name)
        else:
            client.create_database(db_name=milvus_db_name)
            client.use_database(db_name=milvus_db_name)
    else:
        print("No database name provided, using default 'swagger_db'.")
        if "swagger_db" in client.list_databases():
            client.use_database(db_name="swagger_db")
        else:
            print("'swagger_db' not found, creating a new one.")
            client.create_database(db_name="swagger_db")
            client.use_database(db_name="swagger_db")
            milvus_db_name = "swagger_db"

    

    try:  


        # Setup the embeddings
        embeddings = []

        if ollama_embeddings_model:
            try:
                ollama_embeddings = OllamaEmbeddings(model=ollama_embeddings_model)
            except Exception as e:
                raise ValueError(f"Failed to access ollama embeddings model: {e}")
            
            embeddings.append(ollama_embeddings)
        
        if openai_embeddings_model:
            try:
                openai_embeddings = OpenAIEmbeddings(model=openai_embeddings_model)
            except Exception as e:
                raise ValueError(f"Failed to access openai embeddings model: {e}")
            
            embeddings.append(openai_embeddings)
        
        if not ollama_embeddings_model and not openai_embeddings_model:
            raise ValueError("Either Ollama or OpenAI embeddings model is required.")
        

        # Resolve references in the swagger spec, and transform to dict
        # NOTE: this part also does the swagger validation, but can be separated using validate_swagger in utils.swagger
        try:
            swagger_dict = resolve_swagger(swagger_url)
        except Exception as e:
            raise ValueError(f"Failed to resolve swagger from the specified URL: {e}")

        # Setup Milvus vectorstore
        milvus_vectorstore = seutp_milvus_vectorstore(
            embeddings=embeddings,
            db_name=milvus_db_name,
            uri=milvus_uri
        )

        ingestion_kwargs = {}

        if resume_from_checkpoint_file:
            if not os.path.exists(resume_from_checkpoint_file):
                raise ValueError(f"Checkpoint file {resume_from_checkpoint_file} does not exist.")
            else:
                print(f"Resuming from checkpoint file {resume_from_checkpoint_file}")
                ingestion_kwargs["resume"] = True
                ingestion_kwargs["checkpoint_file"] = resume_from_checkpoint_file
        
        # If no checkpoint file is provided, check if the default checkpoint file exists
        if not resume_from_checkpoint_file and os.path.exists("swagger_ingestion_progress.json"):
            resume = typer.confirm("Checkpoint file found. Do you want to resume from it?", default=True)
            if resume:
                print("Resuming from checkpoint file.")
                ingestion_kwargs["resume"] = True
                # Default file name is kept as "swagger_ingestion_progress.json" in the ingest_swagger function

            else:
                print("Starting fresh ingestion.")
                ingestion_kwargs["resume"] = False

        else:
            print("Starting fresh ingestion.")
            ingestion_kwargs["resume"] = False

        # Ingest the swagger spec into Milvus
        documents = ingest_swagger(
            swagger_spec=swagger_dict,
            milvus_vectorstore=milvus_vectorstore,
            endpoint_summary_chain=endpoint_summary_chain,
            **ingestion_kwargs,
        )
    
    except Exception as e:
        print(f"Error during ingestion: {e}")
        raise

    finally:
        client.close()

