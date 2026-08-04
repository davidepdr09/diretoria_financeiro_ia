import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

def consultar_gemini(prompt_sistema: str, prompt_usuario: str) -> str:
    """Função centralizada para enviar prompts analíticos para o Google AI Studio (Gemini)."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Erro: A chave GEMINI_API_KEY não foi configurada no arquivo .env."

    try:
        client = genai.Client(api_key=api_key)
        
        prompt_completo = f"""
        [CONTEXTO DO ESPECIALISTA]
        {prompt_sistema}

        [SITUAÇÃO / DADOS PARA ANÁLISE]
        {prompt_usuario}
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_completo,
        )
        
        return response.text
    except Exception as e:
        return f"Erro ao consultar o Google AI Studio: {str(e)}"

# Alias de compatibilidade
consultar_gemini = consultar_gemini