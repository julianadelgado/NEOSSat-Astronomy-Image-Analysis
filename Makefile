clean:
	rm -rf result_data inference_data

format:
	uv tool run black .

run:
	uv run fastapi dev main.py