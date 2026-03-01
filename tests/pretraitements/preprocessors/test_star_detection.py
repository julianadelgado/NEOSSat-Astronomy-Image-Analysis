import numpy as np
from unittest.mock import patch, MagicMock

from pretraitements.preprocessors.star_detection import StarDetection


def test_star_detection_returns_zero_when_no_sources(tmp_path):
    image = np.zeros((10, 10))
    header = {}

    dao_path = "pretraitements.preprocessors.star_detection.DAOStarFinder"
    wcs_path = "pretraitements.preprocessors.star_detection.WCS"

    with patch(dao_path) as mock_dao, patch(wcs_path):
        mock_instance = MagicMock()
        mock_instance.return_value = None
        mock_dao.return_value = mock_instance

        pre = StarDetection()
        result = pre.run(image, header, tmp_path)

    assert result["stars_detected"] == 0
