import torch
import argparse
from PIL import Image
from moondream import VisionEncoder, TextModel, detect_device
from huggingface_hub import snapshot_download
from queue import Queue
from threading import Thread
from transformers import TextIteratorStreamer
import re

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=str, required=True)
    parser.add_argument("--prompt", type=str, required=False)
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()

    if args.cpu:
        device = torch.device("cpu")
        dtype = torch.float32
    else:
        device, dtype = detect_device()
        if device != torch.device("cpu"):
            print("Using device:", device)
            print("If you run into issues, pass the `--cpu` flag to this script.")
            print()

    image_path = args.image
    prompt = args.prompt

    model_path = snapshot_download("vikhyatk/moondream1")
    vision_encoder = VisionEncoder(model_path).to(device=device, dtype=dtype)
    text_model = TextModel(model_path).to(device=device, dtype=dtype)
    image = Image.open(image_path)
    image_embeds = vision_encoder(image)

    if prompt is None:
        chat_history = ""

        while True:
            question = input("> ")

            result_queue = Queue()

            streamer = TextIteratorStreamer(
                text_model.tokenizer, skip_special_tokens=True
            )

            # Separate direct arguments from keyword arguments
            thread_args = (image_embeds, question, chat_history)
            thread_kwargs = {"streamer": streamer, "result_queue": result_queue}

            thread = Thread(
                target=text_model.answer_question,
                args=thread_args,
                kwargs=thread_kwargs,
            )
            thread.start()

            buffer = ""
            for new_text in streamer:
                buffer += new_text
                if not new_text.endswith("<") and not new_text.endswith("END"):
                    print(buffer, end="", flush=True)
                    buffer = ""
            print(re.sub("<$", "", re.sub("END$", "", buffer)))

            thread.join()

            answer = result_queue.get()
            chat_history += f"Question: {question}\n\nAnswer: {answer}\n\n"
    else:
        print(">", prompt)
        answer = text_model.answer_question(image_embeds, prompt)
        print(answer)
