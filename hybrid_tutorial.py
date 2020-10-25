import html
import io
import os

# Imports the Google Cloud client libraries
from google.api_core.exceptions import AlreadyExists
from google.cloud import texttospeech
from google.cloud import translate_v3beta1 as translate
from google.cloud import vision

# Setting up OS env variables
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r'dsc-vision-ai-workshop2000-c02ebe14126c.json'
PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT"]

# Image detection code
def pic_to_text(infile):
    
    # init the client obj
    client = vision.ImageAnnotatorClient()

    # Opens the input image file
    with io.open(infile, "rb") as image_file:
        content = image_file.read()

    # image detection
    image = vision.Image(content=content)

    # For dense text, use document_text_detection
    # For less dense text, use text_detection
    response = client.document_text_detection(image=image)
    text = response.full_text_annotation.text
    print("Detected text: {}".format(text))

    return text

# Create glossary code
def create_glossary(languages, project_id, glossary_name, glossary_uri):
    """Creates a GCP glossary resource
    Assumes you've already manually uploaded a glossary to Cloud Storage
    ARGS
    languages: list of languages in the glossary
    project_id: GCP project id
    glossary_name: name you want to give this glossary resource
    glossary_uri: the uri of the glossary you uploaded to Cloud Storage
    RETURNS
    nothing
    """

    # Instantiates a client
    client = translate.TranslationServiceClient()

    # Designates the data center location that you want to use
    location = "us-central1"

    # Set glossary resource name
    name = client.glossary_path(project_id, location, glossary_name)

    # Set language codes
    language_codes_set = translate.types.Glossary.LanguageCodesSet(
        language_codes=languages
    )

    # config
    gcs_source = translate.types.GcsSource(input_uri=glossary_uri)

    input_config = translate.types.GlossaryInputConfig(gcs_source=gcs_source)

    # Set glossary resource information
    glossary = translate.types.Glossary(
        name=name, language_codes_set=language_codes_set, input_config=input_config
    )

    parent = f"projects/{project_id}/locations/{location}"

    # Create glossary resource
    # Handle exception for case in which a glossary
    #  with glossary_name already exists
    try:
        operation = client.create_glossary(parent=parent, glossary=glossary)
        operation.result(timeout=90)
        print("Created glossary " + glossary_name + ".")
    except AlreadyExists:
        print(
            "The glossary "
            + glossary_name
            + " already exists. No new glossary was created."
        )    

# Translation code
def translate_text(
    text, source_language_code, target_language_code, project_id, glossary_name
):
    """Translates text to a given language using a glossary
    ARGS
    text: String of text to translate
    source_language_code: language of input text
    target_language_code: language of output text
    project_id: GCP project id
    glossary_name: name you gave your project's glossary
        resource when you created it
    RETURNS
    String of translated text
    """

    # Instantiates a client
    client = translate.TranslationServiceClient()

    # Designates the data center location that you want to use
    location = "us-central1"

    glossary = client.glossary_path(project_id, location, glossary_name)

    glossary_config = translate.types.TranslateTextGlossaryConfig(glossary=glossary)

    parent = f"projects/{project_id}/locations/{location}"

    result = client.translate_text(
        request={
            "parent": parent,
            "contents": [text],
            "mime_type": "text/plain",  # mime types: text/plain, text/html
            "source_language_code": source_language_code,
            "target_language_code": target_language_code,
            "glossary_config": glossary_config,
        }
    )

    # Extract translated text from API response
    return result.glossary_translations[0].translated_text 

# Text-to-speech code
def text_to_speech(text, outfile):
    """Converts plaintext to SSML and
    generates synthetic audio from SSML
    ARGS
    text: text to synthesize
    outfile: filename to use to store synthetic audio
    RETURNS
    nothing
    """

    # Replace special characters with HTML Ampersand Character Codes
    # These Codes prevent the API from confusing text with
    # SSML commands
    # For example, '<' --> '&lt;' and '&' --> '&amp;'
    escaped_lines = html.escape(text)

    # Convert plaintext to SSML in order to wait two seconds
    #   between each line in synthetic speech
    ssml = "<speak>{}</speak>".format(
        escaped_lines.replace("\n", '\n<break time="2s"/>')
    )

    # Instantiates a client
    client = texttospeech.TextToSpeechClient()

    # Sets the text input to be synthesized
    synthesis_input = texttospeech.SynthesisInput(ssml=ssml)

    # Builds the voice request, selects the language code ("en-US") and
    # the SSML voice gender ("MALE")
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.MALE
    )

    # Selects the type of audio file to return
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    # Performs the text-to-speech request on the text input with the selected
    # voice parameters and audio file type
    request = texttospeech.SynthesizeSpeechRequest(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    response = client.synthesize_speech(request=request)

    # Writes the synthetic audio to the output file.
    with open(outfile, "wb") as out:
        out.write(response.audio_content)
        print("Audio content written to file " + outfile) 

def main():

     # Photo from which to extract text
    infile = "resources/chinese-sample.jpg"
    # Name of file that will hold synthetic speech
    outfile = "resources/chinese-sample.mp3"

    # Defines the languages in the glossary
    # This list must match the languages in the glossary
    #   Here, the glossary includes French and English
    glossary_langs = ["zh-Hans", "en"]
    #glossary_langs = ["fr", "en"]
    # Name that will be assigned to your project's glossary resource
    #glossary_name = "chinese-glossary"
    glossary_name = "meme-glossary"
    
    # uri of .csv file uploaded to Cloud Storage
    #glossary_uri = "gs://meme-bucket-3226/meme-glossary.csv"
    glossary_uri = "gs://vision-ai-2020/chinese-glossary.csv"

    create_glossary(glossary_langs, PROJECT_ID, glossary_name, glossary_uri)

    # photo -> detected text
    text_to_translate = pic_to_text(infile)
    # detected text -> translated text
    text_to_speak = translate_text(
        text_to_translate, "zh-Hans", "en", PROJECT_ID, glossary_name
        #text_to_translate, "fr", "en", PROJECT_ID, glossary_name
    )
    # translated text -> synthetic audio
    text_to_speech(text_to_speak, outfile)

if __name__ == "__main__":
    main()