.PHONY: readme-graphics check

# Rebuild the profile graphics in profile/assets/ and the project grid in profile/README.md.
readme-graphics:
	uv run scripts/readme/build_profile_graphics.py

# Report anything out of date without writing.
check:
	uv run scripts/readme/build_profile_graphics.py --check
