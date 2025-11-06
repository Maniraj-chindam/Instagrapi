import google.generativeai as genai

genai.configure(api_key="AIzaSyDmwEiM1gSSjx9Cxz_pNo5-j2jahsrDD34")

for model in genai.list_models():
  print(model.name)