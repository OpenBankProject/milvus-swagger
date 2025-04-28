# Milvus Swagger

A tool for ingesting swagger 2 spec into a Milvus vector database.

example usage 

```
milvus-swagger --milvus-uri "http://localhost:19530" --db-name "test_swagger" --ollama-embeddings-model "bge-m3" --openai-embeddings-model "text-embedding-3-large                                                          
" "http://localhost:8080/obp/v5.1.0/resource-docs/v5.1.0/swagger?content=static"
```