from google import genai

client = genai.Client(api_key="AIzaSyCfeNQaFNGVpUrbb0mq_bPBZ16xM2J-Dy4")

while True:
    data = input("User: ")
    response = client.models.generate_content(
        model="gemini-3-flash-preview", contents=data
    )
    print(f"Chatbot: {response.text}")