import streamlit as st 
import streamlit.components.v1 as components
import cohere
import html
import base64

with st.sidebar:
    API_KEY = st.text_input("Cohere API KEY", key="chat_bot_key", type="password")

st.title("Chatbot BPMN Generator")

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "CHATBOT", "message": "Bienvenido a AUTO CODING!"}]
    st.session_state["messages"].append({"role": "CHATBOT", "message": 
        "Mi misión es ayudarte en la automatización de generación de código para los procesos de tu empresa."})
    st.session_state["messages"].append({"role": "CHATBOT", "message": 
        "Dame todo el contexto que consideres necesario. Cuando consideres que me has dado todo lo que necesito, escribe TERMINAR en el chat."})

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["message"])

prompt = st.chat_input()

if prompt:
    if not API_KEY:
        st.info("No olvides agregar tu API KEY")
        st.stop()

    client = cohere.Client(API_KEY)

    if prompt.lower().strip() == "terminar":
        # Generar BPMN en XML al finalizar
        full_context = "\n".join([m["message"] for m in st.session_state["messages"] if m["role"] == "USER"])

        # PROMPT MEJORADO para layout completo y evitar nodos inconexos
        gen_prompt = (
            "Eres un experto en modelado de procesos de negocio. "
            "Con la siguiente descripción textual de un proceso, genera un archivo BPMN 2.0 válido en formato XML. "
            "Asegúrate de que cada elemento del proceso (tareas, eventos, compuertas y flujos de secuencia) tenga su correspondiente "
            "representación gráfica en el bloque <bpmndi:BPMNDiagram>, incluyendo <bpmndi:BPMNShape> y <bpmndi:BPMNEdge> con coordenadas x/y. "
            "No incluyas ninguna explicación, solo el XML completo.\n\n"
            f"Descripción del proceso:\n{full_context}\n\n"
            "Genera el archivo BPMN XML:"
        )

        response = client.generate(
            model='command-r-plus',
            prompt=gen_prompt,
            max_tokens=3000,
            temperature=0.4
        )

        bpmn_xml = response.generations[0].text.strip()

        # Cierre automático si falta </definitions>
        if not bpmn_xml.strip().endswith("</definitions>") and "<definitions" in bpmn_xml:
            bpmn_xml += "\n</definitions>"

        # Guardar el archivo BPMN
        file_path = "bpmn_output.xml"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(bpmn_xml)

        st.session_state.messages.append({"role": "CHATBOT", "message": "✅ Proceso finalizado. El archivo BPMN ha sido generado como `bpmn_output.xml`."})
        st.chat_message("CHATBOT").write("✅ Proceso finalizado. El archivo BPMN ha sido generado como `bpmn_output.xml`.")

        # Mostrar XML en texto
        with st.expander("Ver XML generado"):
            st.code(bpmn_xml, language="xml")

        # Advertencia si hay flows pero no edges
        if "<sequenceFlow" in bpmn_xml and "<bpmndi:BPMNEdge" not in bpmn_xml:
            st.warning("⚠️ El XML contiene flujos de secuencia pero no incluye elementos gráficos <bpmndi:BPMNEdge>. Algunas flechas pueden aparecer desconectadas.")

        # Visualizar BPMN usando base64 con scroll horizontal y zoom automático
        st.subheader("Visualización del diagrama BPMN")
        bpmn_base64 = base64.b64encode(bpmn_xml.encode("utf-8")).decode("utf-8")

        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <link rel="stylesheet" href="https://unpkg.com/bpmn-js@11.5.0/dist/assets/diagram-js.css" />
          <link rel="stylesheet" href="https://unpkg.com/bpmn-js@11.5.0/dist/assets/bpmn-font/css/bpmn.css" />
          <style>
            html, body {{
              margin: 0;
              padding: 0;
              overflow: hidden;
            }}
            #wrapper {{
              width: 100%;
              overflow-x: auto;
            }}
            #canvas {{
              min-width: 3000px;
              height: 600px;
              border: 1px solid #ccc;
            }}
          </style>
        </head>
        <body>
          <div id="wrapper">
            <div id="canvas"></div>
          </div>
          <script src="https://unpkg.com/bpmn-js@11.5.0/dist/bpmn-viewer.development.js"></script>
          <script>
            const xmlBase64 = "{bpmn_base64}";
            const xml = atob(xmlBase64);

            const viewer = new BpmnJS({{ container: "#canvas" }});

            viewer.importXML(xml).then(() => {{
              viewer.get("canvas").zoom("fit-viewport", "auto");
            }}).catch(err => {{
              document.getElementById("canvas").innerHTML = "<pre>Error cargando BPMN:\\n" + err + "</pre>";
            }});
          </script>
        </body>
        </html>
        """
        components.html(html_code, height=660, scrolling=True)

    else:
        # Continuar con el flujo de chat
        st.chat_message("USER").write(prompt)
        st.session_state.messages.append({"role": "USER", "message": prompt})

        preamble = (
            "Vas a hacer un agente que se encarga de recibir información por parte del usuario, "
            "con el objetivo de generar un BPMN en formato XML al final de la interacción. "
            "Enfócate en escuchar al usuario en lugar de contestar preguntas. "
            "Si tienes una opinión o crees que ciertas preguntas pueden ayudar a mejorar "
            "el contexto del proceso, hazlas."
        )

        response = client.chat(
            chat_history=st.session_state.messages,
            message=prompt,
            preamble=preamble
        )

        msg = response.text
        st.session_state.messages.append({"role": "CHATBOT", "message": msg})
        st.chat_message("CHATBOT").write(msg)
