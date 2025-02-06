from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
import uuid
from app.models import db, User, Role
from app.chroma import get_collection, get_chroma_retriever
from app.vectorizer import vectorize_text, vectorize_sources
from app.langchain import get_rag_chain
import os
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from app.utils.pdf_utils import extract_text_from_pdf_with_pages
from app.utils.text_utils import chunk_text_with_page_numbers
import json
import traceback

UPLOAD_FOLDER = "./uploads"
ALLOWED_EXTENSIONS = {'pdf'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

bp = Blueprint('routes', __name__)

# Home page
@bp.route('/')
def index():
    return render_template('index.html')


# Register route
@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Check if the user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered.')
            return redirect(url_for('routes.register'))

        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)

        # Assign default role
        default_role = Role.query.filter_by(name='User').first()
        if not default_role:
            flash("Default role 'User' does not exist. Please initialize roles.")
            return redirect(url_for('routes.register'))

        user.roles.append(default_role)

        # Save user to the database
        db.session.add(user)
        db.session.commit()

        flash('Registration successful. Please log in.')
        return redirect(url_for('routes.login'))

    return render_template('register.html')


# Login route
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Find user by email
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('routes.dashboard'))

        flash('Invalid credentials.')
        return redirect(url_for('routes.login'))

    return render_template('login.html')


# Logout route
@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('routes.index'))


# Dashboard
@bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=current_user.username)


# Admin panel (example)
@bp.route('/admin')
@login_required
def admin():
    if not current_user.has_role('Admin'):
        return "Access Denied", 403
    return render_template('admin.html')


# Assign roles (admin only)
@bp.route('/assign_role', methods=['GET', 'POST'])
@login_required
def assign_role():
    if not current_user.has_role('Admin'):
        return "Access Denied", 403

    if request.method == 'POST':
        user_email = request.form['email']
        role_name = request.form['role']

        # Find user and role
        user = User.query.filter_by(email=user_email).first()
        role = Role.query.filter_by(name=role_name).first()

        if not user:
            flash(f"User with email {user_email} not found.")
        elif not role:
            flash(f"Role {role_name} not found.")
        else:
            if role not in user.roles:
                user.roles.append(role)
                db.session.commit()
                flash(f"Role {role_name} assigned to user {user_email}.")
            else:
                flash(f"User {user_email} already has the role {role_name}.")

    # Pass users and roles to the template for easier selection
    roles = Role.query.all()
    users = User.query.all()
    return render_template('assign_role.html', users=users, roles=roles)

@bp.route('/users', methods=['GET', 'POST'])
@login_required
def view_users():
    if not current_user.has_role('Admin'):
        return "Access Denied", 403  # Restrict access to admins

    if request.method == 'POST':
        user_id = request.form['user_id']  # Get the user's ID from the form
        role_name = request.form['role']  # Get the selected role name

        # Find the user and role
        user = User.query.get(user_id)
        role = Role.query.filter_by(name=role_name).first()

        if not user:
            flash(f"User not found.", "danger")
        elif not role:
            flash(f"Role '{role_name}' not found.", "danger")
        else:
            # Assign the role if not already assigned
            if role not in user.roles:
                user.roles.append(role)
                db.session.commit()
                flash(f"Role '{role_name}' assigned to user '{user.username}'.", "success")
            else:
                flash(f"User '{user.username}' already has the role '{role_name}'.", "info")

    # Query all users and roles for the template
    users = User.query.all()
    roles = Role.query.all()
    return render_template('view_users.html', users=users, roles=roles)

@bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.has_role('Admin'):
        return "Access Denied", 403  # Restrict to admins

    user = User.query.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('routes.view_users'))

    # Prevent admin self-deletion
    if user.id == current_user.id:
        flash("You cannot delete your own account.", "warning")
        return redirect(url_for('routes.view_users'))

    # Delete the user
    db.session.delete(user)
    db.session.commit()
    flash(f"User '{user.username}' has been deleted.", "success")
    return redirect(url_for('routes.view_users'))

@bp.route('/<collection_name>', methods=['GET', 'POST'])
@login_required
def manage_collection(collection_name):
    # Restrict access to Admins and Editors
    if not current_user.has_role('Admin') and not current_user.has_role('Editor'):
        return "Access Denied", 403

    # Valid collections
    valid_collections = ["sources", "literature", "notes"]
    if collection_name not in valid_collections:
        return "Invalid Collection", 404

    # Get the appropriate collection
    collection = get_collection(collection_name)

    if request.method == 'POST':
        # Add a new document
        doc_id = request.form.get('doc_id')
        content = request.form.get('content')

        if doc_id and content:
            # Check if the document already exists
            existing = collection.get(include=['documents', 'metadatas'])
            if any(meta.get('id') == doc_id for meta in existing['metadatas']):
                flash(f"Document with ID '{doc_id}' already exists in {collection_name}.", "danger")
            else:
                # Add document to the collection
                collection.add(
                    ids=[doc_id],
                    documents=[content],
                    metadatas=[{"id": doc_id, "added_by": current_user.username}]
                )
                flash(f"Document '{doc_id}' added successfully to {collection_name}.", "success")
        else:
            flash("Document ID and content are required.", "danger")

    # Handle delete request
    if request.args.get('delete'):
        doc_id = request.args.get('delete')
        # Ensure the document exists before attempting to delete
        try:
            collection.delete(ids=[doc_id])
            flash(f"Document '{doc_id}' deleted successfully from {collection_name}.", "success")
        except Exception as e:
            flash(f"Error deleting document '{doc_id}': {str(e)}", "danger")
        return redirect(url_for('routes.manage_collection', collection_name=collection_name))

    # Fetch all documents from the collection
    try:
        documents = collection.get(include=['documents', 'metadatas'])
    except Exception as e:
        flash(f"Error fetching documents: {str(e)}", "danger")
        documents = {"documents": [], "metadatas": []}

    return render_template(
        'manage_collection.html', 
        documents=documents, 
        collection_name=collection_name,
        zip=zip
    )

@bp.route('/notes', methods=['GET', 'POST'])
@login_required
def manage_notes():
    # Restrict access to Admins and Editors
    if not current_user.has_role('Admin') and not current_user.has_role('Editor'):
        return "Access Denied", 403

    # Get the Notes collection
    collection = get_collection("notes")

    if request.method == 'POST':
        # Get content from form
        content = request.form.get('content')
        doc_id = request.form.get('doc_id')

        # Automatically generate an ID if none is provided
        if not doc_id:
            doc_id = f"note_{uuid.uuid4().hex[:8]}"  # Generates a unique ID like 'note_ab12cd34'

        if content:
            # Generate embedding using RoBERTa-XLM
            embedding = vectorize_text(content)

            # Add the document to the collection
            collection.add(
                ids=[doc_id],
                documents=[content],
                metadatas=[{"id": doc_id, "added_by": current_user.username}],
                embeddings=[embedding]
            )
            flash(f"Note '{doc_id}' added successfully.", "success")
        else:
            flash("Content cannot be empty.", "danger")

    # Handle delete request
    if request.args.get('delete'):
        doc_id = request.args.get('delete')
        try:
            collection.delete(ids=[doc_id])
            flash(f"Note '{doc_id}' deleted successfully.", "success")
        except Exception as e:
            flash(f"Error deleting note '{doc_id}': {str(e)}", "danger")
        return redirect(url_for('routes.manage_notes'))

    # Fetch all notes
    try:
        documents = collection.get(include=['documents', 'metadatas'])
    except Exception as e:
        flash(f"Error fetching notes: {str(e)}", "danger")
        documents = {"documents": [], "metadatas": []}

    return render_template('manage_notes.html', documents=documents)


@bp.route('/search/<collection_name>', methods=['GET', 'POST'])
@login_required
def search_collection(collection_name):
    # Restrict access to Admins and Editors
    if not current_user.has_role('Admin') and not current_user.has_role('Editor'):
        return "Access Denied", 403

    # Valid collections
    valid_collections = ["sources", "literature", "notes"]
    if collection_name not in valid_collections:
        return "Invalid Collection", 404

    results = None
    zipped_results = []
    query = None

    if request.method == 'POST':
        query = request.form.get('query')
        if not query:
            flash("Search query cannot be empty.", "danger")
            return redirect(url_for('routes.search_collection', collection_name=collection_name))

        # Vectorize the query
        query_embedding = vectorize_text(query)
        print(f"Query Embedding: {query_embedding}")  # Debugging

        # Perform similarity search
        collection = get_collection(collection_name)
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=5,
                include=['documents', 'metadatas']
            )
            print(f"Search Results: {results}")  # Debugging

            # Flatten documents and metadata
            documents = results['documents'][0] if results['documents'] else []
            metadatas = results['metadatas'][0] if results['metadatas'] else []
            zipped_results = list(zip(documents, metadatas))  # Combine documents and metadatas
        except Exception as e:
            flash(f"Error during search: {str(e)}", "danger")
            print(f"Search Error: {str(e)}")  # Debugging

    return render_template(
        'search_collection.html',
        zipped_results=zipped_results,
        query=query,
        collection_name=collection_name
    )



@bp.route('/search_with_langchain/<collection_name>', methods=['GET', 'POST'])
@login_required
def search_with_langchain(collection_name):
    # Check user permissions
    if not current_user.has_role('Admin') and not current_user.has_role('Editor'):
        return "Access Denied", 403

    # Validate collection name
    valid_collections = ["sources", "literature", "notes"]
    if collection_name not in valid_collections:
        return "Invalid Collection", 404

    # Initialize variables
    query = None
    answer = None
    retrieved_documents = None

    if request.method == 'POST':
        # Get user input
        query = request.form.get('query')
        k = int(request.form.get('k', 5))  # Default: 5

        if not query:
            flash("Search query cannot be empty.", "danger")
            return redirect(url_for('routes.search_with_langchain', collection_name=collection_name))

        try:
            # Get ChromaDB retriever
            retriever = get_chroma_retriever(collection_name, model_name="sentence-transformers/all-mpnet-base-v2", k=k)
            rag_chain = get_rag_chain(retriever)  # Uses cached chain if retriever hasn't changed
            #print(rag_chain.input_keys)  # Outputs the expected input keys for the chain

            # Retrieve documents
            documents = retriever.get_relevant_documents(query)
            #print(documents)

            """
            # Format context with document IDs for the RAG chain
            formatted_context = "\n".join([
                f"Document ID: {doc.metadata.get('chapter_id', 'unknown')}, Content: {doc.page_content}"
                for doc in documents
            ])

            print(formatted_context) # This is printed
            """
            # Pass context and query to the RAG chain
            result = rag_chain({"query": query})
            
            #result = rag_chain({"context": formatted_context, "question": query})
            #print(result) # this is not printed
            answer = result["result"]

            # Set retrieved documents for rendering
            retrieved_documents = documents
            #print(retrieved_documents)

        except Exception as e:
            print(e)
            traceback.print_exc()
            flash(f"Error during query processing: {str(e)}", "danger")

    # Render the template with query, answer, and retrieved documents
    return render_template(
        'search_with_langchain.html',
        query=query,
        answer=answer,
        retrieved_documents=retrieved_documents,
        collection_name=collection_name
    )


@bp.route('/literature/delete_all', methods=['POST'])
@login_required
def delete_all_literature():
    # Restrict access to Admins only
    if not current_user.has_role('Admin'):
        return "Access Denied", 403

    print("Deleting collection")

    try:
        # Get the Literature collection
        collection = get_collection("literature")

        # Fetch all metadata to extract IDs
        all_documents = collection.get(include=["metadatas"])
        print(f"All metadatas: {all_documents}")

        # Extract all IDs from metadata
        all_ids = [meta.get("id") for meta in all_documents.get("metadatas", [])]
        print(f"All document IDs: {all_ids}")

        # Delete all documents if any IDs are present
        if all_ids:
            collection.delete(ids=all_ids)
            flash(f"Deleted all {len(all_ids)} documents from the literature collection.", "success")
            print(f"Successfully deleted {len(all_ids)} documents.")
        else:
            flash("No documents found to delete.", "info")

    except Exception as e:
        flash(f"Error deleting all documents: {str(e)}", "danger")
        print(f"Error deleting documents: {str(e)}")

    return redirect(url_for('routes.manage_literature'))




def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/literature', methods=['GET', 'POST'])
@login_required
def manage_literature():
    # Restrict access to Admins and Editors
    if not current_user.has_role('Admin') and not current_user.has_role('Editor'):
        return "Access Denied", 403

    # Get the Literature collection
    collection = get_collection("literature")

    if request.method == 'POST':
        # Handle form data
        file = request.files.get('file')
        author = request.form.get('author')
        title = request.form.get('title')
        year = request.form.get('year')

        # Validate inputs
        if not (file and author and title and year):
            flash("All fields (author, title, year, and PDF) are required.", "danger")
            return redirect(url_for('routes.manage_literature'))

        if not allowed_file(file.filename):
            flash("Invalid file format. Please upload a PDF.", "danger")
            return redirect(url_for('routes.manage_literature'))

        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        file.save(file_path)

        try:
            document_id = f"doc_{uuid.uuid4().hex[:8]}"
            page_texts = extract_text_from_pdf_with_pages(file_path)
            print(page_texts)

            # Chunk the text and create embeddings
            chunks_with_pages = chunk_text_with_page_numbers(page_texts, max_length=300)
            print("Starting embedding")
            for i, chunk in enumerate(chunks_with_pages):
                chunk_id = f"{document_id}_chunk_{i + 1}"
                text = chunk[0]
                page_number = chunk[1]
                embedding = vectorize_text(text)
                print(f"Add {chunk_id} to collection")

                collection.add(
                    ids=[chunk_id],
                    documents=[text],
                    metadatas=[
                        {
                            "chunk_id": chunk_id,
                            "document_id": document_id,
                            "author": author,
                            "title": title,
                            "year": year,
                            "page_number": page_number,
                            "added_by": current_user.username,
                        }
                    ],
                    embeddings=[embedding],
                )

            flash(f"PDF '{title}' processed and added to the collection.", "success")
        except Exception as e:
            flash(f"Error processing PDF: {str(e)}", "danger")
        finally:
            # Clean up the uploaded file
            os.remove(file_path)

        return redirect(url_for('routes.manage_literature'))

    # Handle delete request
    if request.args.get('delete'):
        document_id = request.args.get('delete')
        try:
            all_chunks = collection.get(include=["metadatas"], where={"document_id": document_id})
            chunk_ids = [meta["chunk_id"] for meta in all_chunks["metadatas"]]
            collection.delete(ids=chunk_ids)
            flash(f"Document '{document_id}' deleted successfully.", "success")
        except Exception as e:
            flash(f"Error deleting document '{document_id}': {str(e)}", "danger")
        return redirect(url_for('routes.manage_literature'))

    # Fetch all documents
    try:
        documents = collection.get(include=["metadatas"])
        from collections import defaultdict

        grouped_documents = defaultdict(
            lambda: {"chunk_count": 0, "author": "", "title": "", "year": "", "added_by": ""}
        )
        for metadata in documents["metadatas"]:
            doc_id = metadata["document_id"]
            grouped_documents[doc_id].update(
                {
                    "author": metadata["author"],
                    "title": metadata["title"],
                    "year": metadata["year"],
                    "added_by": metadata["added_by"],
                }
            )
            grouped_documents[doc_id]["chunk_count"] += 1

    except Exception as e:
        flash(f"Error fetching literature: {str(e)}", "danger")
        grouped_documents = {}

    return render_template("manage_literature.html", documents=grouped_documents)



# Allowed extensions for JSON uploads
ALLOWED_JSON_EXTENSIONS = {'json'}

def allowed_json_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_JSON_EXTENSIONS

@bp.route('/upload_json/<collection_name>', methods=['GET', 'POST'])
@login_required
def upload_json(collection_name):
    # Restrict access to Admins and Editors
    if not current_user.has_role('Admin') and not current_user.has_role('Editor'):
        return "Access Denied", 403

    # Valid collections
    valid_collections = ["sources", "literature", "notes"]
    if collection_name not in valid_collections:
        return "Invalid Collection", 404

    if request.method == 'POST':
        # Handle JSON file upload
        file = request.files.get('file')
        if not file or not allowed_json_file(file.filename):
            flash("Invalid file format. Please upload a JSON file.", "danger")
            
            return redirect(url_for('routes.manage_collection', collection_name=collection_name))

        try:
            print("Starting")
            print(file)
            # Load the JSON data
            data = json.load(file)
            print(data)

            # Extract metadata and validate structure
            metadata = data.get("metadata", {})
            chapters = data.get("chapters", [])
            print(len(metadata))
            print(len(chapters))

            if not metadata or not isinstance(chapters, list):
                flash("Invalid JSON structure. Missing metadata or chapters.", "danger")
                return redirect(url_for('routes.manage_collection', collection_name=collection_name))

            # Get ChromaDB collection
            collection = get_collection(collection_name)
            print(collection)

            # Process each chapter
            for chapter in chapters:
                chapter_id = chapter.get("id")
                chapter_url = chapter.get("url", "")
                english_content = chapter.get("english", {}).get("content", "")

                if chapter_id and english_content:
                    # Vectorize only the English content
                    embedding = vectorize_sources(english_content)

                    # Combine global metadata with chapter-specific metadata
                    chapter_metadata = {
                        **metadata,  # Include global metadata
                        "chapter_id": chapter_id,
                        "chapter_url": chapter_url,
                        "latin_content": chapter.get("latin", {}).get("content", ""),
                        "german_content": chapter.get("german", {}).get("content", ""),
                        "english_heading": chapter.get("english", {}).get("heading", ""),
                        "latin_heading": chapter.get("latin", {}).get("heading", "")

                    }

                    try:
                        # Add chapter to collection
                        collection.add(
                            ids=[chapter_id],
                            documents=[english_content],  # Only English content as document
                            metadatas=[chapter_metadata],
                            embeddings=[embedding]
                        )
                        print(f"Successfully added chapter {chapter_id} to the collection.")
                    except Exception as e:
                        print(f"Error adding chapter {chapter_id} to collection: {e}")


                    print(f"Adding to collection: {collection_name}")
                    print(f"Chapter ID: {chapter_id}")
                    print(f"Document: {english_content}")
                    print(f"Metadata: {chapter_metadata}")
                    print(f"Embedding: {embedding}")


                else:
                    flash(f"Skipping chapter with missing 'id' or 'english.content': {chapter}", "warning")

            flash("JSON data successfully imported into the collection.", "success")

        except Exception as e:
            flash(f"Error processing JSON file: {str(e)}", "danger")

        return redirect(url_for('routes.manage_collection', collection_name=collection_name))

    return render_template('manage_collection.html', collection_name=collection_name)

