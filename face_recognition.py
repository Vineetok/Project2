import cv2
import os
import numpy as np
import datetime
import sys
from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client['face_recognition']
users_collection = db['users']
reports_collection = db['reports']

class FaceRecognition:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.known_face_encodings = []
        self.known_face_names = []
        self.process_current_frame = True
        self.matched_celebrities = set()

    def encode_faces(self):
        categories = ['celebrities', 'sportsmen', 'criminals']
        base_path = 'images'

        for category in categories:
            category_path = os.path.join(base_path, category)
            if not os.path.exists(category_path):
                print(f"Folder not found: {category_path}")
                continue

            for image in os.listdir(category_path):
                image_path = os.path.join(category_path, image)
                try:
                    face_image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                    faces = self.face_cascade.detectMultiScale(face_image, scaleFactor=1.1, minNeighbors=5)
                    if len(faces) > 0:
                        self.known_face_encodings.append(face_image)
                        self.known_face_names.append(f"{category}/{image.split('.')[0]}")
                except Exception as e:
                    print(f"Error processing image {image_path}: {e}")
        print("Known faces loaded:", self.known_face_names)

    def run_recognition(self):
        video_capture = cv2.VideoCapture(0)

        if not video_capture.isOpened():
            sys.exit('Video source not found...')

        video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

        celebrity_matches = []

        while True:
            ret, frame = video_capture.read()
            if not ret or frame is None:
                print("Failed to grab frame.")
                break

            if self.process_current_frame:
                gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5)

                for (x, y, w, h) in faces:
                    roi_gray = gray_frame[y:y + h, x:x + w]

                    matches = [cv2.matchTemplate(roi_gray, encoding, cv2.TM_CCOEFF_NORMED).max() for encoding in self.known_face_encodings]
                    name = 'Unknown'
                    confidence = max(matches) if matches else 0

                    if confidence > 0.6:
                        best_match_index = np.argmax(matches)
                        name = self.known_face_names[best_match_index]

                        if name in self.matched_celebrities:
                            print(f"Report for {name} already generated, skipping.")
                            continue

                        self.matched_celebrities.add(name)

                        snapshot_dir = "snapshots"
                        os.makedirs(snapshot_dir, exist_ok=True)
                        snapshot_filename = f"snapshot_{name.replace('/', '')}{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
                        snapshot_path = os.path.join(snapshot_dir, snapshot_filename)
                        cv2.imwrite(snapshot_path, frame)

                        celebrity_matches.append({
                            'Celebrity': name,
                            'Confidence': f"{confidence * 100:.2f}%",
                            'Timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'Image': snapshot_path
                        })

                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        cv2.putText(frame, f'{name} ({confidence * 100:.2f}%)', (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)

            self.process_current_frame = not self.process_current_frame

            cv2.imshow('Face Recognition', frame)
            if cv2.waitKey(1) == ord('q'):
                break

        self.generate_blog_report(celebrity_matches)

        video_capture.release()
        cv2.destroyAllWindows()

    def generate_blog_report(self, celebrity_matches):
        if not celebrity_matches:
            print("No matches with confidence over 60%.")
            return

        for match in celebrity_matches:
            category, name = match['Celebrity'].split('/')

            # Check if a report for this person already exists
            existing_report = reports_collection.find_one({"matches.Celebrity": name})
            if existing_report:
                print(f"Report for {name} already exists in the database.")
                continue

            report_data = {
                "category": category,
                "generated_at": datetime.datetime.now(),
                "matches": [match]
            }
            db['reports'].insert_one(report_data)
            print(f"Report stored in MongoDB with ID: {report_data['_id']}")

if __name__ == '__main__':
    fr = FaceRecognition()
    fr.encode_faces()
    fr.run_recognition()