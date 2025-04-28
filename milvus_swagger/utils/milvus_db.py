from langchain_milvus import BM25BuiltInFunction, Milvus
from typing import Optional, List
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
from langchain_core.runnables.base import Runnable
from markdownify import markdownify
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_ollama.embeddings import OllamaEmbeddings
from pymilvus import Collection, MilvusException, connections, db, utility
from rich import print
from rich.progress import Progress
import uuid
import hashlib
import os
import datetime
import json

URI = "http://localhost:19530"

def seutp_milvus_vectorstore(embeddings: List[Embeddings], db_name: str, uri: Optional[str] = None) -> Milvus:

    if uri is None:
        print("No URI provided, using default URI.")
        uri = URI

    # Make sure the vector fields align with the embedding models being passed
    vector_fields = []
    for i, embedding_model in enumerate(embeddings):
        if isinstance(embedding_model, OpenAIEmbeddings):
            vector_field_name = "openai_dense"
        elif isinstance(embedding_model, OllamaEmbeddings):
            vector_field_name = "ollama_dense"
        else:
            vector_field_name = f"dense{i}"

        vector_fields.append(vector_field_name)
        
    # Add the sparse field if using the BM25BuiltInFunction
    vector_fields.append("sparse")

    vectorstore = Milvus(
        embedding_function=embeddings,
        builtin_function=BM25BuiltInFunction(output_field_names="sparse"),
        vector_field=vector_fields,
        connection_args={"uri": uri, "token": "root:Milvus", "db_name": db_name},
        consistency_level="Strong",
        collection_name="swagger_endpoints",
        drop_old=True,  # set to True if seeking to drop the collection with that name if it exists
    )

    return vectorstore
    

def ingest_swagger(
        swagger_spec: dict, 
        milvus_vectorstore: Milvus, 
        endpoint_summary_chain: Optional[Runnable] = None,
        checkpoint_file: str = "swagger_ingestion_progress.json",
        log_file: str = "swagger_ingestion_log.json",
        resume: bool = False,
        ) -> List[Document]:
    """
    Ingests the swagger specification into the Milvus vectorstore.
    This function processes each endpoint from the swagger specification,
    converts the endpoint details into Document objects, and adds them to the Milvus vectorstore.
    It skips endpoints with 'Dynamic-Entity' tags, summarizes descriptions when a chain is provided,
    and generates deterministic UUIDs for each endpoint.
    Args:
        swagger_spec (dict): The swagger specification as a dictionary
        db_namespace (uuid.UUID): The namespace UUID used for generating deterministic UUIDs
        endpoint_summary_chain (Optional[Runnable]): An optional chain for summarizing endpoint descriptions
        checkpoint_file (str): Path to checkpoint file to save/resume progress
        resume (bool): Whether to resume from previous checkpoint
    Returns:
        List[Document]: A list of Document objects created from the swagger spec endpoints
    """
    
    # Load processed endpoints from checkpoint file if it exists and resume is enabled
    processed_endpoints = {}
    if resume and os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, 'r') as f:
                processed_endpoints = json.load(f)
            print(f"Resuming from checkpoint with {len(processed_endpoints)} previously processed endpoints")
        except Exception as e:
            print(f"Error loading checkpoint file: {e}")

    # Count endpoints to be processed
    total_endpoints_count = 0
    for path, endpoint in swagger_spec["paths"].items():
        for method, properties in endpoint.items():
            # Skip already processed endpoints if resuming
            endpoint_key = f"{method}:{path}"
            if resume and endpoint_key in processed_endpoints:
                continue
            total_endpoints_count += 1

    documents = []
    endpoints_processed = 0
    with Progress() as progress:
        # this context manager is just for the progress bar
        task = progress.add_task("[cyan]Ingesting swagger spec into Milvus vectorstore...", total=total_endpoints_count)

        for path, endpoint in swagger_spec["paths"].items():
            for method, properties in endpoint.items():
                
                # Create a unique key for this endpoint
                endpoint_key = f"{method}:{path}"

                # Skip if already processed and resuming
                if resume and endpoint_key in processed_endpoints:
                    continue
                
                    
                try:
                    
                    props = properties.copy()
                    
                    # Summarize the description of the endpoint in markdown
                    if endpoint_summary_chain is not None:
                        summary_chain_response = endpoint_summary_chain.invoke({"raw_description": properties['description']})
                        summarized_description = summary_chain_response.content
                    else:
                        summarized_description = properties['description']
                    

                    # Change the description from HTML to markdown format
                    props['description'] = markdownify(props['description'])
                    
                    # Generate deterministic UUID from OperationID
                    m = hashlib.md5()
                    m.update(props['operationId'].encode('utf-8'))
                    endpoint_uuid = uuid.UUID(m.hexdigest())

                    # Convert non-string properties to strings
                    for field in ['tags', 'parameters', 'security']:
                        if field in props and isinstance(props[field], list):
                            props[field] = str(props[field])


                    endpoint_metadata = {'method': method.upper(),'path': path,} | props

                    endpoint_description_string = f"""
                    {method.upper()} {path} - {props['operationId']}

                    description: {summarized_description}

                    tags: {props['tags']}

                        parameters: {props['parameters']}

                        responses: {props['responses']}
                    """

                    doc = Document(
                        id=endpoint_uuid,
                        page_content=endpoint_description_string,
                        metadata=endpoint_metadata,

                    )

                    milvus_vectorstore.add_documents([doc], ids=[doc.id])
                    documents.append(doc)

                    # Update checkpoint after successful processing
                    processed_endpoints[endpoint_key] = {
                        "uuid": str(endpoint_uuid),
                        "processed_at": str(datetime.datetime.now()),
                    }

                    # Save checkpoint periodically (e.g., every 10 endpoints)
                    if len(processed_endpoints) % 5 == 0:
                        with open(checkpoint_file, 'w+') as f:
                            json.dump(processed_endpoints, f)
    
                    print(f"{method.upper()} {path} processed...")

                except Exception as e:
                    print(f"Error processing {method.upper()} {path}: {e}")
                    # Save checkpoint on error to enable resuming
                    with open(checkpoint_file, 'w+') as f:
                        json.dump(processed_endpoints, f)
                    raise

                progress.update(task, advance=1) # update the progress bar

        # Final checkpoint save
        with open(checkpoint_file, 'w') as f:
            json.dump(processed_endpoints, f)

    # At the end of the function, after successful completion:
    print("Completed ingesting swagger spec into Milvus vectorstore.")

    # Rename the checkpoint file to log file upon successful completion
    if os.path.exists(checkpoint_file):
        try:
            # Generate a timestamp string for the log file
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # Get the filename and extension
            log_name, log_ext = os.path.splitext(log_file)
            # Create the new log file name with timestamp
            timestamped_log_file = f"{log_name}_{timestamp}{log_ext}"

            os.rename(checkpoint_file, timestamped_log_file)
            print(f"Renamed checkpoint file to {timestamped_log_file} for historical reference")
        except Exception as e:
            print(f"Warning: Couldn't rename checkpoint file to log: {e}")

    return documents