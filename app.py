# %%
import streamlit as st
from google import genai
from streamlit_mermaid import st_mermaid  # To render the diagram
import io
import traceback  # To show detailed errors if needed

# %%
# --- Page Configuration ---
st.set_page_config(
    page_title="LaTeX Paper Lemma Flowchart Generator",
    page_icon=" LFC ",  # You can use an emoji or path to an icon file
    layout="wide",
)

# --- Sidebar for Inputs ---
st.sidebar.header("Configuration")

# 1. API Key Input
# link to https://aistudio.google.com/apikey
st.sidebar.markdown(
    "Get your API key from [Google AI Studio](https://aistudio.google.com/apikey)."
)

api_key = st.sidebar.text_input(
    "Enter your Gemini API Key",
    type="password",
    help="Get your key from Google AI Studio.",
)

model_name = st.sidebar.text_input(
    "Model Name",
    value = "gemini-2.0-flash",
    help="Enter the model name you want to use (e.g., gemini-2.0-flash, gemini-2.5-pro).",
)

# 2. File Uploader
uploaded_file = st.sidebar.file_uploader(
    "Upload your .tex paper",
    type=["tex"],
    help="Upload the main LaTeX file of your paper.",
)

st.sidebar.info(
    "Ensure your .tex file contains standard LaTeX commands for lemmas, theorems, propositions, etc. (\lemma, \theorem, \proposition, \corollary, \label, \ref, \cite)."
)

# --- Main App Area ---
st.title("LemmaTree")
st.markdown(
    "This app analyzes your uploaded `.tex` file using Google Gemini to generate a Mermaid JS flowchart visualizing the dependency between lemmas, theorems, and other results."
)

# --- Processing Logic ---
if "mermaid_code" not in st.session_state:
    st.session_state.mermaid_code = None
if "error_message" not in st.session_state:
    st.session_state.error_message = None

# Add a button to trigger the generation process
if st.sidebar.button("Generate Flowchart", disabled=(not api_key or not uploaded_file)):
    st.session_state.mermaid_code = None  # Reset previous results
    st.session_state.error_message = None  # Reset previous errors

    if api_key and uploaded_file:
        try:
            # --- Read File Content ---
            stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
            tex_content = stringio.read()

            if not tex_content.strip():
                st.session_state.error_message = (
                    "Error: The uploaded .tex file appears to be empty."
                )

            else:
                # Show a spinner while processing
                with st.spinner(
                    "Analyzing document and generating flowchart... This may take a moment."
                ):
                    # --- Initialize Gemini Client --- NEW WAY
                    try:
                        client = genai.Client(api_key=api_key)
                    except Exception as client_init_error:
                        st.session_state.error_message = f"Failed to initialize Gemini Client. Check API Key? Error: {client_init_error}"
                        st.stop()  # Stop execution if client fails to initialize

                    # --- Define the Prompt ---
                    # Clear instructions for the LLM
                    prompt = f"""
                    Analyze the following LaTeX document content. Your goal is to generate a flowchart diagram using Mermaid JS syntax (specifically `graph TD;` for top-down).

                    The flowchart should depict the dependency structure of defined results like lemmas, theorems, propositions, and corollaries within the paper.
                    Show how earlier results (e.g., Lemma 1, Proposition 2) are cited or used as direct inputs or prerequisites to prove subsequent results (e.g., Theorem 3, Lemma 4).

                    Focus on explicit dependencies mentioned via commands like \\ref{{...}}, \\cite{{...}} (if referencing prior internal results labelled similarly), or textual references (e.g., "by Lemma 1", "using Proposition 2").
                    Represent each result (Lemma, Theorem, Proposition, Corollary) as a node. Use arrows (`-->`) to indicate dependency (e.g., `Lemma1 --> Theorem1`).
                    Use the labels found in the LaTeX code (e.g., `lem:flow`, `thm:main`) or the numbered identifiers (e.g., Lemma 2.1, Theorem 3) as node IDs/text where possible. If labels are complex, simplify them.

                    Generate *only* the Mermaid JS code block, starting with `graph TD;` or `graph LR;`. Do not include any explanation before or after the code block.

                    LaTeX Document Content:
                    ```latex
                    {tex_content}
                    ```

                    Mermaid JS Flowchart:
                    """

                    # --- Call Gemini API using Client --- NEW WAY
                    try:
                        # Select the model directly in the generate_content call
                        # Using gemini-1.5-flash as a good default.
                        # Use gemini-1.5-pro for potentially more complex analysis if needed.

                        response = client.models.generate_content(
                            model=model_name,
                            contents=[prompt],  # Pass the prompt string as content
                            # Optional: Add generation_config={} here if needed
                        )
                        generated_text = response.text

                        # Basic cleaning: remove potential markdown code block fences
                        if generated_text.strip().startswith("```mermaid"):
                            generated_text = generated_text.split("```mermaid", 1)[1]
                        if generated_text.strip().startswith("```"):
                            generated_text = generated_text.split("```", 1)[1]
                        if generated_text.strip().endswith("```"):
                            generated_text = generated_text.rsplit("```", 1)[0]

                        st.session_state.mermaid_code = generated_text.strip()

                    except Exception as api_error:
                        # Catch specific API errors if possible, otherwise generic
                        if hasattr(api_error, "message"):
                            error_detail = api_error.message
                        else:
                            error_detail = str(api_error)
                        st.session_state.error_message = f"Error calling Gemini API ({model_name}): {error_detail}\n\nDetails:\n{traceback.format_exc()}"

        except UnicodeDecodeError:
            st.session_state.error_message = "Error: Could not decode the .tex file. Please ensure it is UTF-8 encoded."
        except (
            genai.types.generation_types.BlockedPromptException
        ) as blocked_error:  # Keep this specific error handling
            st.session_state.error_message = (
                f"Content generation blocked by API safety settings: {blocked_error}"
            )
        except Exception as e:
            st.session_state.error_message = f"An unexpected error occurred: {e}\n\nDetails:\n{traceback.format_exc()}"

    elif not api_key:
        st.warning("Please enter your Gemini API key in the sidebar.")
    elif not uploaded_file:
        st.warning("Please upload a .tex file in the sidebar.")

# --- Display Results or Errors ---
if st.session_state.error_message:
    st.error(st.session_state.error_message)

if st.session_state.mermaid_code:
    st.subheader("Generated Mermaid JS Code")
    st.code(st.session_state.mermaid_code, language="mermaid")

    st.subheader("Rendered Flowchart")
    try:
        # Use streamlit-mermaid to render the diagram
        st_mermaid(st.session_state.mermaid_code, height=600)  # Adjust height as needed
        st.caption(
            "Note: The accuracy of the flowchart depends on the AI's interpretation of the LaTeX structure and explicit references within the text."
        )
    except Exception as render_error:
        st.error(
            f"Could not render the Mermaid diagram. The generated code might be invalid. Error: {render_error}"
        )
        st.warning("Please check the generated Mermaid code above for syntax errors.")

elif not st.session_state.error_message and not uploaded_file and not api_key:
    st.info(
        "Please provide your Gemini API key and upload a .tex file in the sidebar, then click 'Generate Flowchart'."
    )
elif not st.session_state.error_message and (not uploaded_file or not api_key):
    st.info("Provide both API Key and .tex file, then click 'Generate Flowchart'.")
