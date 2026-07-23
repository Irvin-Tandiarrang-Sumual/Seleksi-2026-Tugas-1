from scraper.config import COURSES, LOG_OUTPUT_DIR
from scraper.pipeline import Pipeline
from utils.logger import Logger


def main() -> None:
    logger = Logger(output_dir=LOG_OUTPUT_DIR)
    try:
        pipeline = Pipeline(logger=logger)
        pipeline.run(COURSES)
    finally:
        logger.close()


if __name__ == "__main__":
    main()
