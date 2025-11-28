# gradio_ui.py
import gradio as gr
import pandas as pd
from backend_app import process_query

def call_backend(question: str):
    if not question or not question.strip():
        return {
            "status": "error",
            "final_answer": "Please provide a question.",
            "generated_sql": "",
            "sql_result": "",
            "model_used": "",
            "explanation": "",
            "table": pd.DataFrame()
        }

    # Call the local process_query function directly
    data = process_query(question)

    # Normalize SQL result to DataFrame if possible
    sql_result = data.get("sql_result")

    if isinstance(sql_result, str):
        try:
            import json
            sql_result = json.loads(sql_result)
        except json.JSONDecodeError:
            # If it's not valid JSON, keep it as a string; the next line will handle it.
            pass

    if isinstance(sql_result, str):
        try:
            import ast
            sql_result = ast.literal_eval(sql_result)
        except (ValueError, SyntaxError):
            # If it's not a valid Python literal, keep it as a string
            pass
    
    df = pd.DataFrame(sql_result) if isinstance(sql_result, list) else pd.DataFrame({"raw": [str(sql_result)]}) if sql_result is not None else pd.DataFrame()
    data['table'] = df

    return data


with gr.Blocks(title="Pharma Data QA — Gradio UI") as demo:
    gr.Markdown("### Pharma Data QA Interface")

    with gr.Column():
        gr.Markdown("**Question**")
        with gr.Row():
            inp = gr.Textbox(
                show_label=False,
                placeholder="e.g. Which territory has the highest prescription volume this quarter?",
                scale=4
            )
            run = gr.Button("Run", variant="primary", scale=1)


    # Large boxes for Generated SQL and Final Answer (prominent)
    with gr.Row():
        sql_box = gr.Textbox(label="Generated SQL", lines=10, interactive=False)
        final_box = gr.Textbox(label="Final answer / explanation", lines=10, interactive=False)

    # Data table showing SQL results (kept under the big boxes)
    result_table = gr.Dataframe(label="SQL result (table)")
    explanation_box = gr.Textbox(label="Explanation", lines=2, interactive=False)

    # Bottom-most row: model used, status, and download
    with gr.Row():
        model_box = gr.Textbox(label="Model used", interactive=False)
        status_box = gr.Textbox(label="Status / Error", interactive=False)

    def on_run(q):
        out = call_backend(q)
        # Return order must match the outputs list in run.click
        return (
            out.get("generated_sql"),
            out.get("final_answer"),
            out.get("table"),
            out.get("explanation"),
            out.get("model_used"),
            out.get("status")
        )

    # wire up the click — inputs and outputs order must match the on_run return tuple
    run.click(
        on_run,
        inputs=[inp],
        outputs=[sql_box, final_box, result_table, explanation_box, model_box, status_box],
    )


if __name__ == "__main__":
    demo.launch()
