#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

import cv2


video_directory = 'videos'
frame_directory = 'frames'


def make_directory(directory: str):
  if not os.path.exists(directory):
    os.makedirs(directory)


def new_name(name: str):
  new = ''
  for char in name:
    new += char if char.isdigit() or char.isalpha() else '_'
  return new


def video_to_frames():
  make_directory(video_directory)

  # SEE: https://stackoverflow.com/a/33399711
  for video in os.listdir(video_directory):
    vidcap = cv2.VideoCapture(os.path.join(video_directory, video))
    success,image = vidcap.read()
    count = 0

    print(f"[!] Video to read: {video}")

    video_name = new_name(video)
    image_directory = os.path.join(frame_directory, video_name)
    make_directory(image_directory)

    while success:
      image_name = os.path.join(image_directory, f"frame_{count}.jpg")
      cv2.imwrite(image_name, image)
      success,image = vidcap.read()
      print('Read a new frame: ', success)
      count += 1

    break


def crop_avatar_by_coordinates(imgray, frame, x, y, w, h):
  """Need &imgray for other operations
  """
  new_name = f"frame_{frame}.jpg"
  print(new_name)
  crop_img = imgray[y:y+h, x:x+w]
  cv2.imwrite(new_name, crop_img)


def frame_to_avatar(image_name):
  im = cv2.imread(image_name)
  imgray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)

  ret, thresh = cv2.threshold(imgray, 127, 255, 0)
  contours, hierarchy = cv2.findContours(
    thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
  )

  avatar = 0

  for c in contours:
    x, y, w, h = cv2.boundingRect(c)
    if w > 50 and h > 50:
      fe = abs((x+y) - (w+h))

      if fe > 500:
        continue

      if (fe < 100):
        continue

      if abs(w - h) > 100:
        continue

      crop_avatar_by_coordinates(imgray, f"__{avatar}", x, y, w, h)
      avatar += 1


def main():
  for video in os.listdir(frame_directory):
    # frames/video
    video_directory = os.path.join(frame_directory, video)
    for idx, _ in enumerate(video_directory):
      image_name = os.path.join(video_directory, f"frame_{idx}.jpg")



if __name__ == '__main__':
  frame_to_avatar(os.path.join('test', 'frame_158.jpg'))
