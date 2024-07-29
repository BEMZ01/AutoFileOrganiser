import base64
import random
import time
from pprint import pprint
from openai import OpenAI, NotFoundError
from dotenv import load_dotenv
import os
import watchdog
from watchdog.observers.polling import PollingObserver
from watchdog.events import PatternMatchingEventHandler
import logging


class AI:
    def __init__(self):
        self.client = OpenAI(
            base_url=str(os.getenv("AI_BASE_URL")),
            api_key=str(os.getenv("AI_API_KEY")),  # api_key is required, but unused for local models
        )
        # test the connection
        try:
            models = self.client.models.list()
        except Exception as e:
            raise Exception("Failed to connect to the OpenAI API. Please check your API key and base URL.")
        print(f"Connected to OpenAI API. Available models: \n - {'\n - '.join([model.id for model in models.data])}")
        # check if the model is one of the available models (remove anything after a colon)
        if os.getenv("AI_MODEL_NAME").upper() not in [model.id.split(":")[0].upper() for model in models.data]:
            raise Exception(
                f"Model not found. Please check the model name in the .env file. ({os.getenv('AI_MODEL_NAME')})")
        else:
            print(f"Model found: {os.getenv('AI_MODEL_NAME')}")
        self.history = [{"role": "system", "content": "You are a helpful assistant that helps humans organise their "
                                                      "files. You will be sent a file name, and some metadata about "
                                                      "the file. You will then need to respond with a JSON object. An"
                                                      "example would be: {'file_name': 'cat.png', 'tags': ['animal',"
                                                      "'cute','cat'], 'main_catagory': 'images', 'emoji': "
                                                      "'🐱', 'comment': 'This is a picture of a cat!'}."
                                                      " You MUST start with the JSON object."}]

    def send_message(self, message: str, image_base64: str = None):
        try:
            if os.getenv("AI_ALLOW_UPLOADING_IMAGES").lower() == "true" and image_base64 is not None:
                response = self.client.chat.completions.create(
                    model=str(os.getenv("AI_MODEL_NAME")),
                    messages=self.history + [{"role": "user", "content": message}, {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"}}]
                )
            else:
                response = self.client.chat.completions.create(
                    model=str(os.getenv("AI_MODEL_NAME")),
                    messages=self.history + [{"role": "user", "content": message}]
                )
        except NotFoundError as e:
            raise Exception("Model not found. Please check the model name in the .env file.")
        self.history.append({"role": "assistant", "content": response.choices[0].message.content})
        return response.choices[0].message.content

    def reset(self):
        self.history = []


def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def is_image(file_path):
    return file_path.lower().endswith(("jpg", "jpeg", "png", "gif", "webp", "bmp"))


def on_created(event):
    print(f"hey, {event.src_path} has been created!")


def on_deleted(event):
    print(f"what the f**k! Someone deleted {event.src_path}!")


def on_modified(event):
    print(f"hey buddy, {event.src_path} has been modified")


def on_moved(event):
    print(f"ok ok ok, someone moved {event.src_path} to {event.dest_path}")


# if env file is not found, raise an exception
if os.path.exists('.env'):
    load_dotenv()
else:
    print("Warning: .env file not found! Assuming environment variables are already set.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    print("Starting AI...")
    ai = AI()
    print("Initialising watchdog...")
    # convert comma separated string to list
    extensions = os.getenv("FILE_EXTENSION_BLACKLIST").split(",")
    if os.getenv("FILE_EXTENSION_INVERT").lower() == "true":
        # if the invert flag is set, invert the blacklist to a whitelist (use the ignore_patterns)
        patterns = []
        ignore_patterns = [f"*.{extension}" for extension in extensions]
        print("Whitelisted extensions:")
    else:
        # otherwise, use the blacklist
        patterns = [f"*.{extension}" for extension in extensions]
        ignore_patterns = None
        print("Blacklisted extensions:")
    for extension in extensions:
        print(f" - {extension}")
    my_event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, False, True)
    my_event_handler.on_created = on_created
    my_event_handler.on_deleted = on_deleted
    my_event_handler.on_moved = on_moved
    path = os.getenv("FILE_WATCHER_PATH")
    print(f"Starting watchdog observer at {path} ...")
    my_observer = PollingObserver()
    my_observer.schedule(my_event_handler, path, recursive=True)
    my_observer.start()
    print("Watchdog observer started?")
    try:
        while my_observer.is_alive():
            time.sleep(0.1)
    except KeyboardInterrupt:
        my_observer.stop()
    my_observer.join()
