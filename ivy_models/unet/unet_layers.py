import ivy


class UNetDoubleConv(ivy.Module):
    def __init__(self, in_channels, out_channels, mid_channels=None):
        if not mid_channels:
            mid_channels = out_channels
        self.double_conv = ivy.Sequential(
            ivy.Conv2D(in_channels, mid_channels, [3, 3], 1, 1, with_bias=False),
            ivy.BatchNorm2D(mid_channels),
            ivy.ReLU(),
            ivy.Conv2D(mid_channels, out_channels, [3, 3], 1, 1, with_bias=False),
            ivy.BatchNorm2D(out_channels),
            ivy.ReLU(),
        )
        super().__init__()

    def _forward(self, x):
        return self.double_conv(x)


class UNetDown(ivy.Module):
    """Downscaling with maxpool then double conv"""

    def __init__(self, in_channels, out_channels):
        self.maxpool_conv = ivy.Sequential(
            ivy.MaxPool2D(2, 2, 0), UNetDoubleConv(in_channels, out_channels)
        )
        super().__init__()

    def _forward(self, x):
        return self.maxpool_conv(x)


class UNetUp(ivy.Module):
    """Upscaling then double conv"""

    def __init__(self, in_channels, out_channels, bilinear=True):
        # if bilinear, use the normal convolutions to reduce the number of channels
        if bilinear:
            self.up = ivy.interpolate(
                scale_factor=2, mode="bilinear", align_corners=True
            )
            self.conv = UNetDoubleConv(in_channels, out_channels, in_channels // 2)
        else:
            self.up = ivy.Conv2DTranspose(in_channels, in_channels // 2, [2, 2], 2, 0)
            self.conv = UNetDoubleConv(in_channels, out_channels)
        super().__init__()

    def _forward(self, x1, x2):
        x1 = self.up(x1)
        # input is BHWC
        diff_H = x2.shape[1] - x1.shape[1]
        diff_W = x2.shape[2] - x1.shape[2]

        pad_width = (
            (0, 0),
            (diff_H - diff_H // 2, diff_H // 2),
            (diff_W // 2, diff_W - diff_W // 2),
            (0, 0),
        )

        x1 = ivy.constant_pad(x1, pad_width)
        x = ivy.concat((x2, x1), axis=3)
        return self.conv(x)


class UNetOutConv(ivy.Module):
    def __init__(self, in_channels, out_channels):
        self.conv = ivy.Conv2D(in_channels, out_channels, [1, 1], 1, 0)
        super(UNetOutConv, self).__init__()

    def _forward(self, x):
        return self.conv(x)
