for bg in 0 10 20
do
    # python plot_merged_cdf.py online-boutique/test-${bg}/W300-E100-C100-S100
    python plot_merged_cdf.py online-boutique/test-bg${bg}/W400-E100-C100-S100
    python plot_merged_cdf.py online-boutique/test-bg${bg}/W500-E100-C100-S100
    python plot_merged_cdf.py online-boutique/test-bg${bg}/W600-E100-C100-S100
    python plot_merged_cdf.py online-boutique/test-bg${bg}/Wc500a1500e200s200-E100-C100-S100
    python plot_merged_cdf.py online-boutique/test-bg${bg}/Wc500a1500e200s200-Ec300a1000e200s100-C100-S100
done