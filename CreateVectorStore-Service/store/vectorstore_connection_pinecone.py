from pinecone.grpc import PineconeGRPC
from pinecone import ServerlessSpec
from langchain_core.documents import Document
from langchain_pinecone import Pinecone
from typing import List, Optional, Any, Dict
from models.schema import StoreArguments
from db.db_config import vectorstore_info_collection

import os
from dotenv import load_dotenv
load_dotenv()

from store.get_embedings_llm import Embedings

class ExtendedPinecone(Pinecone):
    def __init__(self, api_key: str, index_name: str, namespace: str):
        """Initialize Pinecone client and index."""
        self.api_key = api_key
        self.index_name = index_name
        self.namespace = namespace
        pinecone = PineconeGRPC(api_key=self.api_key)
        self.index = pinecone.Index(index_name)
    
    def delete_documents_by_metadata(self, intent: str, region_id: str, branch: str):
        """Delete documents from Pinecone based on metadata and namespace."""
        filter_expr = {
            "intent": intent,
            "region_id": region_id,
            "branch": branch
        }
        print(f"Deleting documents in namespace '{self.namespace}' with filter: {filter_expr}")
        self.index.delete(filter=filter_expr, namespace=self.namespace)
    
    def add_documents(self, documents: List[Document], embedding_function: Any):
        """Add documents to Pinecone index under the specified namespace."""
        vectors = []
        for doc in documents:
            vector = embedding_function.embed_query(doc.page_content)
            metadata = doc.metadata
            id = metadata.get("id") or metadata.get("intent")

            if not id:
                raise ValueError("Document must have an 'id' or 'intent' in metadata.")

            vectors.append((id, vector, metadata))

        self.index.upsert(vectors, namespace=self.namespace)
    

    @classmethod
    def from_documents(
        cls,
        documents: List[Document],
        embedding_function: Any,
        api_key: str,
        index_name: str,
        namespace: str
    ) -> "ExtendedPinecone":
        """Return Pinecone store initialized with documents and embeddings."""
        instance = cls(api_key, index_name, namespace)

        # Extract unique metadata keys to identify duplicates
        sources_to_replace = set(
            (
                doc.metadata.get("intent"),
                doc.metadata.get("region_id"),
                doc.metadata.get("branch")
            )
            for doc in documents
            if "intent" in doc.metadata and "region_id" in doc.metadata and "branch" in doc.metadata
        )

        for intent, region_id, branch in sources_to_replace:
            if intent and region_id and branch:
                instance.delete_documents_by_metadata(intent, region_id, branch)

        return instance.from_documents(documents, embedding_function)



class VectorStore:

    def __init__(self, **kwargs: StoreArguments):
        self.store_type: str = kwargs.get('store_type', None)
        self.namespace_name: str = kwargs.get('collection_name', None)
        self.embedding_type: str = kwargs.get('embedding_type', None)
        self.page_content: Optional[str] = kwargs.get('page_content', None)
        self.data: list = kwargs.get('data', [])
        self.old_collection_name = kwargs.get('old_collection_name', None)
        self.api_key = kwargs.get('pinecone_api_key', None)
        self.namespace = kwargs.get('collection_name', None)
        self.index_name = kwargs.get("index_name")
    
    def create_documents(self, file_extension: str):
        """Create documents based on input data."""
        documents = []
        for item in self.data:
            if file_extension in ['pdf', 'json', 'text']:
                documents.append(Document(page_content=item.get('content'), metadata=item.get('metadata', {})))
        return documents
    
    async def store_documents(self, file_extension: str, clearOldDocuments=False):
        """Store documents in Pinecone."""
        if not self.store_type:
            return None

        documents = self.create_documents(file_extension)
        embedding_function = Embedings(embedding_type=self.embedding_type).get_embedings()

        if self.store_type == 'pinecone':
            pinecone_store = ExtendedPinecone(
                api_key=self.api_key,
                index_name=self.collection_name,
                namespace=self.namespace
            )

            if clearOldDocuments:
                if self.old_collection_name:
                    pinecone_store.index.delete(namespace=self.old_collection_name)
                pinecone_store.index.delete(namespace=self.namespace)
                result = await vectorstore_info_collection.update_many(
                    {"vectorstore_collection": {"$in": [self.old_collection_name, self.collection_name]}},
                    {"$set": {"replaced": True}}
                )
                print(f"{result.modified_count} document(s) updated as replaced.")

            ExtendedPinecone.from_documents(
                documents,
                embedding_function,
                api_key=self.api_key,
                index_name=self.index_name,
                namespace=self.namespace
            )
            return True
    
    @staticmethod
    def get_store(embedings, store_type: str = 'pinecone', index_name: str = None, api_key: str = None, namespace: str = None):
        if store_type == 'pinecone':
            return ExtendedPinecone(
                api_key=api_key,
                index_name=index_name,
                namespace=namespace
            )
        return None
    
