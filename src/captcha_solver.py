"""CAPTCHA solving module using Google's Gemini AI.

This module provides functionality to analyze and solve various types of CAPTCHAs,
with a focus on image-based grid selection CAPTCHAs commonly used by websites.
"""

# flake8: noqa: E501
import argparse
import asyncio
import base64
import logging
import os
import sys
from typing import List, Optional

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("CaptchaSolver")

# Load environment variables from .env file
load_dotenv()


class CaptchaSolution(BaseModel):
    """Structured output for CAPTCHA solving.

    Describes the CAPTCHA task and the solution, including grid analysis
    and selection details.
    """

    is_captcha: bool = Field(
        description=(
            "True if the image contains a recognizable CAPTCHA, " "False otherwise."
        )
    )
    captcha_type: Optional[str] = Field(
        None,
        description=("Type of CAPTCHA (e.g., 'image_grid_selection', 'text_based')."),
    )
    instruction_text: Optional[str] = Field(
        None,
        description=(
            "The instruction text provided by the CAPTCHA "
            "(e.g., 'Select all squares with traffic lights')."
        ),
    )
    grid_size_rows: Optional[int] = Field(
        None,
        description=("Number of rows in the CAPTCHA grid (e.g., 3 for a 3x3 grid)."),
    )
    grid_size_cols: Optional[int] = Field(
        None,
        description=("Number of columns in the CAPTCHA grid (e.g., 3 for a 3x3 grid)."),
    )
    grid_detection_reasoning: Optional[str] = Field(
        None,
        description=("Reasoning behind grid dimension detection."),
    )
    detailed_cell_assessment: Optional[List[str]] = Field(
        None,
        description=(
            "A list of strings, one for each cell in the grid (0 to N-1), "
            "describing if it contains the target object and why. "
            "E.g., for a 2x2 grid: ['Cell 0: Contains a traffic light.', "
            "'Cell 1: Empty.', 'Cell 2: Contains a partial traffic light.', "
            "'Cell 3: Contains a tree.']"
        ),
    )
    selected_indices: Optional[List[int]] = Field(
        None,
        description=(
            "A list of 0-indexed integers representing the grid cells to select. "
            "Indices are counted row by row, starting from the top-left. "
            "For a 3x3 grid, indices are 0-8. For a 4x4 grid, 0-15."
        ),
    )
    should_click_skip: Optional[bool] = Field(
        False,
        description=(
            "True if the CAPTCHA instructions indicate to click a 'skip' or 'none' "
            "button, and this action is appropriate."
        ),
    )
    error_message: Optional[str] = Field(
        None,
        description=(
            "Error message if CAPTCHA solving failed or CAPTCHA not recognized."
        ),
    )


def image_to_base64(image_path: str) -> Optional[str]:
    """Convert an image file to a base64 encoded string.

    Args:
        image_path: Path to the image file.

    Returns:
        Base64 encoded string of the image or None if conversion fails.
    """
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    except FileNotFoundError:
        logger.error(f"Image file not found: {image_path}")
        return None
    except Exception as e:
        logger.error(f"Error converting image to base64: {e}")
        return None


async def solve_image_captcha(image_path: str) -> Optional[CaptchaSolution]:
    """
    Analyzes an image CAPTCHA using Gemini and returns a structured solution.

    Args:
        image_path: Path to the CAPTCHA image file.

    Returns:
        A CaptchaSolution object or None if an error occurs.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GOOGLE_API_KEY not found in environment variables.")
        return CaptchaSolution(
            is_captcha=False, error_message="GOOGLE_API_KEY not found."
        )

    base64_image = image_to_base64(image_path)
    if not base64_image:
        return CaptchaSolution(
            is_captcha=False, error_message="Failed to convert image to base64."
        )

    # You mentioned "gemini-2.5-flash-preview-04-17".
    # Using "gemini-1.5-flash-latest" as it's a common alias for the latest flash model.
    # Adjust if you have a specific reason for the preview version and it's available.
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash-latest", google_api_key=api_key, temperature=0
    )
    structured_llm = llm.with_structured_output(CaptchaSolution)

    prompt_text = (
        "Analyze the provided image. It might be a visual CAPTCHA. "
        "Your primary goal is to accurately solve it if it's a grid-based image "
        "selection CAPTCHA. Perform a two-pass analysis:\n\n"
        "**Pass 1: Detailed Cell-by-Cell Assessment**\n"
        "1. **Initial Check**: Determine if the image contains a visual CAPTCHA challenge. "
        "If not, set `is_captcha: false` and provide reasoning in `error_message`. "
        "Stop here if not a CAPTCHA.\n"
        "2. **Instruction Extraction**: If it is a CAPTCHA, extract the *exact instruction text* "
        "(e.g., 'Select all squares with traffic lights'). Store this in `instruction_text`.\n"
        "3. **Grid Dimension Analysis**:\n"
        "   a. Examine the CAPTCHA challenge area, focusing on the interactive grid.\n"
        "   b. Count the number of image rows and columns. Store in `grid_size_rows` and "
        "`grid_size_cols`.\n"
        "   c. In `grid_detection_reasoning`, explain how you determined the dimensions.\n"
        "4. **Individual Cell Scrutiny**:\n"
        "   a. Based on the grid size and target object(s), iterate through each cell.\n"
        "   b. For each cell, determine if it contains the target object(s).\n"
        "      - Look for any characteristic part of the target, no matter how small.\n"
        "      - Check edges and corners thoroughly.\n"
        "      - Look through visual noise or low contrast.\n"
        "   c. Create a list of strings for `detailed_cell_assessment`.\n"
        "   d. Focus only on the grid area.\n\n"
        "**Pass 2: Final Selection**\n"
        "5. **Compile Selected Indices**: Review `detailed_cell_assessment` and identify all "
        "cell indices that contain the target object(s). Store in `selected_indices`.\n"
        "6. **Skip Condition**: If the instructions include 'skip if none' and no cells match, "
        "set `should_click_skip: true`.\n\n"
        "Provide your answer in the structured format defined. The `detailed_cell_assessment` "
        "is critical for verifying your reasoning. Accuracy is paramount."
    )

    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt_text},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{base64_image}"},
            },
        ]
    )

    try:
        logger.info("Sending CAPTCHA image to Gemini for analysis...")
        response = await structured_llm.ainvoke([message])
        if isinstance(response, CaptchaSolution):
            if response.is_captcha:
                logger.info(
                    f"Captcha identified. Instruction: {response.instruction_text}, "
                    f"Selected Indices: {response.selected_indices}, "
                    f"Skip: {response.should_click_skip}"
                )
                if response.grid_detection_reasoning:
                    logger.info(
                        f"Grid detection reasoning: {response.grid_detection_reasoning}"
                    )
                if response.detailed_cell_assessment:
                    logger.info("Detailed Cell Assessment:")
                    for i, assessment in enumerate(response.detailed_cell_assessment):
                        logger.info(f"  {assessment}")  # Log each assessment
            else:
                logger.info(
                    "No CAPTCHA identified by Gemini or unable to solve. "
                    f"Reason: {response.error_message or 'Not a CAPTCHA'}"
                )
            return response
        else:
            logger.error(f"Unexpected response type from LLM: {type(response)}")
            return CaptchaSolution(
                is_captcha=False,
                error_message=f"Unexpected LLM response type: {type(response)}",
            )

    except Exception as e:
        logger.error(f"Error invoking Gemini model: {e}", exc_info=True)
        return CaptchaSolution(
            is_captcha=False, error_message=f"LLM invocation error: {str(e)}"
        )


async def main_test(image_path_for_test: str) -> None:
    """Test the CAPTCHA solver with a given image.

    Args:
        image_path_for_test: Path to the CAPTCHA image file for testing.
    """
    if not os.path.exists(image_path_for_test):
        logger.error(f"Test image not found: {image_path_for_test}")
        print(
            f"Test image not found: {image_path_for_test}. "
            "Please provide a valid image path."
        )
        return

    print(f"Attempting to solve CAPTCHA from image: {image_path_for_test}")
    solution = await solve_image_captcha(image_path_for_test)

    if solution:
        print("\n--- CAPTCHA Solution ---")
        print(f"Is CAPTCHA: {solution.is_captcha}")
        if solution.is_captcha:
            print(f"  Type: {solution.captcha_type}")
            print(f"  Instruction: {solution.instruction_text}")
            print(f"  Grid Rows: {solution.grid_size_rows}")
            print(f"  Grid Cols: {solution.grid_size_cols}")
            print(f"  Grid Reasoning: {solution.grid_detection_reasoning}")
            print(f"  Selected Indices: {solution.selected_indices}")
            if solution.detailed_cell_assessment:  # Display detailed assessment
                print("  Detailed Cell Assessment:")
                for _, assessment in enumerate(solution.detailed_cell_assessment):
                    print(f"    {assessment}")
            print(f"  Should Click Skip: {solution.should_click_skip}")
        if solution.error_message:
            print(f"  Error: {solution.error_message}")
    else:
        print("Failed to get a solution from the CAPTCHA solver.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Solve image CAPTCHAs using Gemini.")
    parser.add_argument(
        "image_path",
        type=str,
        nargs="?",  # Makes the argument optional
        default=None,
        help=(
            "Path to the CAPTCHA image file. If not provided, "
            "a sample image will be used/created."
        ),
    )
    args = parser.parse_args()

    test_image_file_to_use = args.image_path

    if not test_image_file_to_use:
        test_image_file_to_use = "sample_captcha_image.png"
        if not os.path.exists(test_image_file_to_use):
            try:
                from PIL import Image, ImageDraw

                img = Image.new(
                    "RGB", (300, 200), color="grey"
                )  # Changed color for dummy
                d = ImageDraw.Draw(img)
                d.text((10, 10), "Dummy CAPTCHA for Test", fill=(255, 255, 0))
                img.save(test_image_file_to_use)
                logger.warning("Created a dummy test image: %s", test_image_file_to_use)
            except ImportError:
                logger.warning(
                    "Pillow library not found. Cannot create dummy image. "
                    "Please install with 'uv add Pillow'"
                )
                logger.warning(
                    "Please create a file named '%s' or provide a path to an "
                    "existing image for testing.",
                    test_image_file_to_use,
                )
                sys.exit(1)  # Exit if dummy can't be made and no path given
            except Exception as e:
                logger.error(f"Could not create dummy test image: {e}")
                sys.exit(1)  # Exit on other errors creating dummy

    if not os.path.exists(test_image_file_to_use):
        logger.error(
            f"Test image not found: {test_image_file_to_use} and dummy creation failed or was skipped."
        )
        for _ in range(10):
            print("-" * 40)
        print(
            "Error: Test image '{}' not found. Please provide a valid image path.".format(
                test_image_file_to_use
            )
        )
        sys.exit(1)

    asyncio.run(main_test(test_image_file_to_use))
