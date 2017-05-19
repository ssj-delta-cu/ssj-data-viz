import unittest
import tempfile
import os

import numpy
import arcpy

import generate_spatial_comparisons as g

class DateTest(unittest.TestCase):
	def test_days_in_month(self):
		self.assertEqual(g.get_days_in_month_by_band_and_year(4, 2015), 28)  # Feb 2015 has 28 days
		self.assertEqual(g.get_days_in_month_by_band_and_year(4, 2016), 29)  # Feb 2016 has 29 days
		self.assertEqual(g.get_days_in_month_by_band_and_year(11, 2016), 30)  # Sept 2016
		self.assertEqual(g.get_days_in_month_by_band_and_year(10, 2016), 31)  # Aug 2016


class GenerateDataTest(unittest.TestCase):
	"""
	def test_mean(self):

		zero_lists = [[[1,1,1],
					   [1,1,1],
					   [1,1,1],]] * 12  # makes it a 12 band raster where each band is 9 cells of 0

		ten_lists = [[[10,10,10],
					   [10,10,10],
					   [10,10,10],]] * 12  # makes it a 12 band raster where each band is 9 cells with the value 10

		origin_point = arcpy.Point(0, 0)

		zero_numpy = numpy.array(zero_lists)
		ten_numpy = numpy.array(ten_lists)

		cellsize = 30

		zero_raster = arcpy.NumPyArrayToRaster(zero_numpy, origin_point, cellsize, cellsize)
		ten_raster = arcpy.NumPyArrayToRaster(ten_numpy, origin_point, cellsize, cellsize)
		temp_output_zero = tempfile.mktemp(prefix="spatial_comparisons_zero", suffix=".tif")
		temp_output_ten = tempfile.mktemp(prefix="spatial_comparisons_ten", suffix=".tif")
		zero_raster.save(temp_output_zero)
		ten_raster.save(temp_output_ten)  # need to save these out because code can't fully handle raster object inputs

		rasters = [temp_output_zero, temp_output_ten]

		mean_raster = tempfile.mktemp(prefix="spatial_comparisons_unit_test_mean_", suffix=".tif")
		std_dev_raster = tempfile.mktemp(prefix="spatial_comparisons_unit_test_std_dev_", suffix=".tif")

		print(mean_raster)
		print(std_dev_raster)

		g.get_statistics_for_year(rasters, 2016, mean_raster, std_dev_raster)
	"""
	def test_run_real_data(self):
		base_path = os.path.split(os.path.split(__file__)[0])[0]
		mean_output_2015 = os.path.join(base_path, "outputs", "2015_mean_test.tif")
		std_output_2015 = os.path.join(base_path, "outputs", "2015_std_test.tif")
		mean_output_2016 = os.path.join(base_path, "outputs", "2016_mean_test.tif")
		std_output_2016 = os.path.join(base_path, "outputs", "2016_std_test.tif")
		g.get_statistics_for_year(g.rasters[2015], 2015, mean_path=mean_output_2015, std_path=std_output_2015, raster_base_path=os.path.join(base_path, "spatial_comparisons"), debug=True)
		g.get_statistics_for_year(g.rasters[2016], 2016, mean_path=mean_output_2016, std_path=std_output_2016, raster_base_path=os.path.join(base_path, "spatial_comparisons"), debug=True)



if __name__ == "__main__":
	unittest.main()