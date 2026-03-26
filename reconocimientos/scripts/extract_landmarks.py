import cv2
import mediapipe as mp
import numpy as np
import os

mp_hands = mp.solutions.hands


def extract_landmarks_from_video(video_path, max_frames=30):
    cap = cv2.VideoCapture(video_path)
    frames_data = []

    with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as hands:
        while cap.isOpened() and len(frames_data) < max_frames:
            ret, frame = cap.read()
            if not ret:
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(frame_rgb)

            frame_landmarks = np.zeros((2, 21, 3), dtype=np.float32)

            if results.multi_hand_landmarks:
                for i, hand_landmarks in enumerate(results.multi_hand_landmarks[:2]):
                    for j, lm in enumerate(hand_landmarks.landmark):
                        frame_landmarks[i][j] = [lm.x, lm.y, lm.z]

            frames_data.append(frame_landmarks.reshape(42, 3))

    cap.release()

    if len(frames_data) < max_frames:
        padding = [np.zeros((42, 3), dtype=np.float32)] * (max_frames - len(frames_data))
        frames_data.extend(padding)

    return np.array(frames_data)  # shape: (30, 42, 3)


def process_all_videos(queryset, output_dir, max_frames=30):
    os.makedirs(output_dir, exist_ok=True)
    processed = 0
    errors = 0

    for video_seña in queryset:
        video_path = video_seña.video.path
        output_path = os.path.join(output_dir, f"{video_seña.id}.npy")

        try:
            video_seña.procesando = True
            video_seña.save(update_fields=['procesando'])

            landmarks = extract_landmarks_from_video(video_path, max_frames=max_frames)
            np.save(output_path, landmarks)

            video_seña.procesando = False
            video_seña.procesado = True
            video_seña.save(update_fields=['procesando', 'procesado'])

            processed += 1
            print(f"[OK] {video_seña.label} — {video_seña.id} ({landmarks.shape})")

        except Exception as e:
            video_seña.procesando = False
            video_seña.save(update_fields=['procesando'])
            errors += 1
            print(f"[ERROR] {video_seña.id}: {e}")

    print(f"\nCompletado: {processed} OK, {errors} errores")
    return processed, errors