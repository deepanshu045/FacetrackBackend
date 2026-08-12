import face_recognition
import numpy as np


def generate_face_encoding(image_path: str):
    """
    Returns:
        encoding -> numpy array
        None -> if image is invalid
    """

    image = face_recognition.load_image_file(image_path)

    locations = face_recognition.face_locations(image)

    if len(locations) == 0:
        return None

    if len(locations) > 1:
        return None

    encodings = face_recognition.face_encodings(
        image,
        locations
    )

    if len(encodings) != 1:
        return None

    return encodings[0]