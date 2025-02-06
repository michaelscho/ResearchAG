from langchain_community.llms.ollama import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from flask import current_app

#model = "deepseek-r1:14b"
model = "llama3.1"
# Singleton for LLM
def get_llama_llm():
    cache = current_app.config.get('CACHE', {})
    if 'llama_llm' not in cache:
        cache['llama_llm'] = Ollama(model=model)  # Ensure Ollama is running
        current_app.config['CACHE'] = cache  # Update the cache in the app config
    return cache['llama_llm']

# Singleton for the Main Prompt Template
def get_main_prompt_template():
    """
    This is the final prompt (for the combined documents + user question).
    We define placeholders: {context} = merged documents, {question} = user's question.
    """
    cache = current_app.config.get('CACHE', {})
    if 'main_prompt_template' not in cache:
        main_prompt = """
        You are an expert research assistant. 
        You will answer research question related to the Decretum by Burchard of Worms.
        He was the author of a canon law collection of twenty books known as the Decretum Burchardi. 
        Your answer will be based on the following documents taken from the Decretum Burchardi.

        Give 'chapter_id' of document in question in parentheses behind mention of document:

        Documents:
        {context}

        Question:
        {question}

        Answer:
        """
        cache['main_prompt_template'] = PromptTemplate(
            template=main_prompt,
            # Must match the placeholders in the template
            input_variables=["context", "question","chapter_id"],
        )
        current_app.config['CACHE'] = cache
    return cache['main_prompt_template']


def get_document_prompt_template():
    """
    This prompt template is used for each retrieved document. 
    It inserts 'chapter_id' from doc.metadata plus the doc's page_content.
    """
    cache = current_app.config.get('CACHE', {})
    if 'document_prompt_template' not in cache:
        # We define placeholders: {page_content} and {metadata} 
        # because the "stuff" chain passes each doc's page_content and metadata to this prompt.
        doc_prompt = """
        
        {page_content}
        """
        cache['document_prompt_template'] = PromptTemplate(
            template=doc_prompt,
            # 'metadata' is a dictionary, 'page_content' is a string
            input_variables=["page_content"]#, "metadata"],
        )
        current_app.config['CACHE'] = cache
    return cache['document_prompt_template']


# Singleton for the RetrievalQA Chain
def get_rag_chain(retriever):
    cache = current_app.config.get('CACHE', {})
    chain_cache_key = f"rag_chain_{id(retriever)}"
    if chain_cache_key not in cache:
        llm = get_llama_llm()
        main_prompt = get_main_prompt_template()        # Final prompt
        print(main_prompt)
        doc_prompt = get_document_prompt_template()     # Per-document prompt
        print(doc_prompt)
        # We override question_key="question" since your final prompt uses {question}
        # We also specify the document_prompt so it includes chapter_id from metadata.
        rag_chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            chain_type="stuff",
            chain_type_kwargs={
                "prompt": main_prompt,
                "document_prompt": doc_prompt,         # custom doc-level prompt
                
            },
            return_source_documents=True,
        )
        cache[chain_cache_key] = rag_chain
        current_app.config['CACHE'] = cache  # Update the cache in the app config
    return cache[chain_cache_key]

# https://github.com/langchain-ai/langchain/issues/1136