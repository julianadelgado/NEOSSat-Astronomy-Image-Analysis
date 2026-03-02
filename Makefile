clean:
	rm -rf result_data inference_data

test:
	uv run pytest

format:
	uv tool run black .

run:
	uv run fastapi dev main.py

view-fits:
	uv run python scripts/view_fits.py

clean-images:
	uv run python scripts/remove_similar_images.py