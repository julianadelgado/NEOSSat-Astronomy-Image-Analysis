from unittest.mock import MagicMock, patch

import numpy as np

from preprocessing.preprocessors.star_detection_legacy import StarDetectionLegacy


def test_star_detection_legacy_returns_zero_when_no_sources(tmp_path):
    image = np.zeros((10, 10))
    header = {}

    dao_path = "preprocessing.preprocessors.star_detection_legacy.DAOStarFinder"
    wcs_path = "preprocessing.preprocessors.star_detection_legacy.WCS"

    with patch(dao_path) as mock_dao, patch(wcs_path):
        mock_instance = MagicMock()
        mock_instance.return_value = None
        mock_dao.return_value = mock_instance

        pre = StarDetectionLegacy()
        result = pre.run(image, header, tmp_path)

    assert result["stars_detected"] == 0
