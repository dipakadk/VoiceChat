from store.get_embedings_llm import Embedings;
from langchain.schema import Document
from langchain.vectorstores.milvus import Milvus 
from typing import Optional
from store.database.milvus import MilvusVectoreStore
from models.schema import StoreArguments
from langchain_core.embeddings import Embeddings
from db.db_config import vectorstore_info_collection
import os
from dotenv import load_dotenv
load_dotenv()
DB_NAME= os.getenv('DB_NAME') or 'General'

from typing import List, Optional, Any, Union,Dict

class ExtendedMilvus(Milvus):
    
        def get_documents(self, expr: str, output_fields: Optional[List[str]] = None) -> List[dict] | None:
            """Get documents with metadata filters applied.

            Args:
                expr: Expression to filter documents, e.g., "intent == '/path/to/intent'".
                output_fields: List of fields to include in the result. If None, all fields are returned.

            Returns:
                List[dict]: List of documents with the specified fields.
            """
            from pymilvus import MilvusException

            if self.col is None:
                print("No existing collection to retrieve documents.")
                return None

            try:
                query_result = self.col.query(
                    expr=expr,
                    output_fields=output_fields if output_fields else ["*"]  # "*" returns all fields
                )
            except MilvusException as exc:
                print("Failed to retrieve documents: %s error: %s", self.collection_name, exc)
                raise exc

            return query_result
        
        
        
        @classmethod
        def from_documents(
            cls,
            documents: List[Document],
            embedding: Embeddings,
            **kwargs: Any,
        ) -> 'ExtendedMilvus':
            """Return VectorStore initialized from documents and embeddings.

            This method first deletes any existing documents that share the same `source`
            as the incoming documents and then adds the new documents.
            """
            instance = cls(
                embedding_function=embedding,
                collection_name=kwargs.get('collection_name', 'default_collection'),
                connection_args=kwargs.get('connection_args', {}),
            )
            print("Before extraction")
            # Extract unique sources from the incoming documents
            sources_to_replace = set(
                (doc.metadata.get("intent"), doc.metadata.get("region_id"), doc.metadata.get("branch"))
                for doc in documents
                if "intent" in doc.metadata and "region_id" in doc.metadata and "branch" in doc.metadata
            )
            print("After extraction")
            print(sources_to_replace)
            for intent,region_id,branch in sources_to_replace:
                # if intent and region_id and branch:
                    # Delete existing documents with this source
                instance.delete_documents_by_intent_and_region(intent,region_id,branch)
            


            # Add new documents using the existing base class logic
            return super().from_documents(documents, embedding, **kwargs)

        def delete_documents_by_intent_and_region(self, intent: str, region_id:str, branch:str):
            """Delete documents from the collection by source."""
            print("Entered deleted")
            expr = f"intent == '{intent}' and region_id == '{region_id}' and branch == '{branch}'"
            print("Expression is ====",expr)
            ids = self.get_pks(expr)
            print("ids done====")
            if ids:
                self.delete(ids=ids)
                print("Deleted Ids====")
            print("Here after If")
                
                
class VectorStore:
    
    def __init__(self,**kwargs:StoreArguments):
        self.store_type: str = kwargs.get('store_type',None)
        self.collection_name: str =  kwargs.get('collection_name',None)
        self.embedding_type: str =  kwargs.get('embedding_type', None)
        self.page_content: Optional[str] =  kwargs.get('page_content',None)
        self.data: list =kwargs.get('data',[])
        self.host: str = kwargs.get('host')
        self.port: int = kwargs.get('port')
        self.db_name: str = kwargs.get('db_name') or DB_NAME
        self.old_collection_name=kwargs.get('old_collection_name',None) 
    """
      create Document according to your csv data
      args:
        file_extension: str (type of uploaded file extensions )
    """
    def create_documents(self,file_extension:str):
        documents=[]
        for item in self.data:
            if file_extension =='pdf':
                documents.append(Document(page_content=item.get('content'),metadata={}))
            if file_extension == 'json':
                documents.append(Document(page_content=item.get('content'), metadata={}))
            if file_extension=='text':
                documents.append(Document(page_content=item.get('content'), metadata={}))
        return documents
    
    """create Document and store it in provided vector store database"""
    async def store_documents(self,file_extension:str,clearOldDocuments=False):
        print(self.store_type,file_extension,"===================type==================")
        """identfy which vector store can we going to used by checking store_type"""
        mivusStore= MilvusVectoreStore(host=self.host,port=self.port,db_name=self.db_name);
        mivusStore._connect_and_create_db()
        

        if not self.store_type:
            return None
        if clearOldDocuments:
            await mivusStore.drop_collection(self.collection_name)
            if self.old_collection_name:
                await mivusStore.drop_collection(self.old_collection_name)
            result = await vectorstore_info_collection.update_many(
                {"vectorstore_collection": {"$in": [self.old_collection_name, self.collection_name]}},
                {"$set": {"replaced": True}}
             )
            # Check how many documents were updated
            if result.modified_count > 0:
                print(f"{result.modified_count} document(s) with vectorstore_collection '{self.collection_name}' have been updated with deleted: true.")
            else:
                print("No documents found with the specified vectorstore_collection.")
        if self.store_type=='milvus':
            if file_extension =='combined':
                documents= self.data
                embedings=Embedings(embedding_type=self.embedding_type).get_embedings();
                ExtendedMilvus.from_documents(documents,embedings,collection_name=self.collection_name,connection_args={'host':self.host,'port':self.port,'db_name':self.db_name})
                return True

            
    @staticmethod     
    def get_store(embedings,store_type:str='milvus',collection_name:str=None,host:str=None,port:str=None):
        if store_type == 'milvus':
            return ExtendedMilvus(embedings, connection_args={'host':host, 'port':port,'db_name':DB_NAME}, collection_name=collection_name)
        else:
            return None