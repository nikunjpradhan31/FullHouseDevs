# Blackjack Computer Vision Edge Analyzer (FullHouseDevs)

An advanced application that utilizes real-time Computer Vision to track live Blackjack games and calculate the player's edge on the fly. 

The system uses a custom-trained YOLOv8 object detection model to recognize cards, categorizes them into Dealer and Player zones, and streams detection events via Apache Kafka to a Game Engine. The backend then maintains the game state and runs Monte Carlo simulations to provide real-time strategic edge analysis.

##  Architecture & Core Components

This project is structured as a microservices architecture communicating over Kafka:

- **`cv_backend/`**: Real-time card detection service using OpenCV and Ultralytics YOLOv8. It captures frames, identifies cards, locks in stable detections over multiple frames, and produces events to the Kafka broker.
- **`game_engine_backend/`**: Consumes card events, maintains the current Blackjack game state, and executes real-time Monte Carlo simulations to calculate player edge and optimal strategies.
- **`simulations/`**: Standalone offline tools for backtesting Blackjack strategies, running high-volume game simulations, and evaluating expected values.
- **`cv_models/`**: Stores exported object detection models (e.g., YOLO weights in `.pt` or `.onnx` formats).
- **`apache_kafka/`**: Configurations and setup for the Kafka messaging broker used to decouple computer vision events from the game engine logic.

##  Tech Stack

- **Python 3.11+** managed by [uv](https://github.com/astral-sh/uv)
- **Computer Vision**: OpenCV, Ultralytics (YOLOv8), PyTorch
- **Messaging**: Apache Kafka, `aiokafka`
- **APIs**: FastAPI, Uvicorn
- **Libraries**: Numpy

