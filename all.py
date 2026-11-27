#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全站聚合 v1 —— 影探4K / 搜剧AI / 星光影库 / 免扫云盘 / 红果短剧 五源合并为一条线路

功能
1) 影片按季显示：每条线路名 = “源-提供方-第N季《片名》”，多季自动合并，另加“全季连播 N集”。
2) 三级分类：一级只按内容形态（热榜/电影/剧集/动漫/综艺/纪录片/短剧/少儿），
   二级是筛选（分类 / 频道 / 地区 / 年份 / 来源 / 排序），三级才是影片列表；
   同片跨源自动去重，分类页 pagecount 固定 999 无限下拉。
3) 播放前实时探测画质（HLS/TS/MP4/MKV：分辨率/HDR/杜比声道），有 4K 时只显示 4K 线路，
   普通线路隐藏；4K 线路播不出来时自动用隐藏线路顶上。

分类结构（核心改动）
  一级 8 个：🔥今日热榜 / 🎬电影 / 📺剧集 / 🌸动漫 / 🎤综艺 / 🌍纪录片 / ⚡短剧 / 🧸少儿
  二级（筛选，每个大类一套）：排序(综合/热度/首映/高分) · 类型 · 地区 · 年代 · 来源
    （短剧把“类型/频道”放在排序后：真人剧/漫剧/AI剧 + 红果题材）
  三级：影片列表（多源合并、同片去重、无限下拉）
  说明：原来的“影探·电影 / 搜剧·剧集 / 红果·真人剧 …”二十多个并列全部收进“来源”筛选，
        源不再单独占分类位；选了题材/地区/年份时只向支持该维度的源取数，避免混入无关结果。

部署
  把本文件放到 /sdcard/py/全站聚合.py，TVBox 配置：
  {"key":"全站聚合","name":"全站聚合","type":3,"api":"py/全站聚合.py","searchable":1,
   "quickSearch":1,"filterable":1,"ext":{}}

ext 可选项（都可省略）
  hide_sd      1/0   探测到 4K 后隐藏普通线路（默认 1）
  probe        1/0   实时画质探测（默认 1）
  probe_max    8     最多同时探测多少条候选线路
  probe_budget 9     探测总预算（秒）
  season_merge 1/0   跨源/跨季合并（默认 1）
  sources      "yt,sj,xg,wp,hg"  启用的源
  pan_sites    "多多,木偶,欧歌"   网盘源参与列表/搜索的站
"""

import base64
import hashlib
import json
import os
import re
import sys
import tempfile
import threading
import time
import zlib
from concurrent.futures import ThreadPoolExecutor, wait

import requests

try:
    from base.spider import Spider as _BaseSpider
except Exception:
    try:
        sys.path.append('..')
        from base.spider import Spider as _BaseSpider
    except Exception:
        class _BaseSpider(object):
            pass

# =============================================================================
# 一、内嵌的五个源（原文件原样保留，各自独立命名空间，互不污染）
# =============================================================================
_EMBED = {}
_EMBED['yt'] = ('影探4K.py',
    b"eNrFPGt3E0eW3/UraiBMSyBLMjaG1cbhGGMWNpCwQGYm43h02lLbbtxSK+qWjIK9x0nGYAM2hEfCw0BIyIRNwishAfyA/zKrbsmf"
    b"2J+w91ZVd1c/BIaTPetzgqTqW7du3VfdR3U2ko7NHSSvF9TSaJZUzZGOHTgS20is1Yf2wjfd775Yudq8+ND5OZ46apDm98v27Xlr"
    b"9sHawxXr21/IhDI8ZtZI88crzc+e2r/csWa+a6w+b16807z6d3Kwbo7pJXK4rBaUyn9Pfwao4Yn9yyVAbJ86ZS/+ZH95srH8m33x"
    b"GWC0507bi0skbRTycqWQLtfTDh2pcv3Fyhm2xtrMfHP1HpHLKrFu/UhGVE3JptPRk2JqsaxXTDIsG0pPt/PrqKGXnO8VxflmqkX3"
    b"e7WiaepwqixXDCXmgX5cVQzTiI1U9CLpr9TLpp7qV8tjSoVwkL6Bw76nH5iqljooF5DDDky1VJYLsZhZqWdjBP4oPBKYMiibHDjG"
    b"tJhyLK+UTbKPDg5UKnqFTeNQRt2gP+ETyDXHUnK5rJQKcSmVkhLrwR97d+BD0kukOpBoyqXucSm29/3DR3BozDTLwNp80Uhp9Xrd"
    b"rKXyJSnWf+Bwjs+ZOLhtuHZMz3fVa9v36Lv+Y+C9PX+t9u3JDHzwYaV7/5G6FAOBt77/1r5xzl74zjr77YuV2ZG6gI2A4O3LX1v3"
    b"br9YmQPYrZmtPR2dncS6d8P+9TQoSWv6U9QjKghjX6G3i7TuPbBWL1mPf7Zmv167AvPOMNTNa4/gC9mWyQAeWIeyaoAyTwUVVEvk"
    b"IEWSKo+ViaaWFNLTlSVHKrhvYupkVDFJuaKXlYpZJxIogET0EVLSSx368FElbwKBTIE5jR1be4h1e56RuS3dQxpPbtvXbzWe3rTv"
    b"LjeWTgAJjSfT1rPT5PgGMDFlQzaT3FA0RjdkNzCOWLcfth59t2EKEMMm0Ohm7qydPGvP/WifPUtAOJ3/2bmVWOcWmrfute7dtr98"
    b"AJywHy1TNl4FeEK2gxCaq1+s3fq1ufS89fg+rNmaeda6dz/dnH1ofXeyNbeUbp06b99YTDdWLq/NPE7vAhsizbtzMGXt+jfW4gPr"
    b"+jT554nzpNhV3cFkQMgOQNv9LgGOrl14Bjjrxe7xo8cEqTWenEapFMvd6eJ4DUWwdA4Qgzk3Vi+AaEh3ppvtif2tXQcRf27Pf2PP"
    b"nmt9enFt+mpj6YvmtcvEPFrQJ0qaLhdAeUupCR2xp4Gv/9V8vgIwJK/p1UK+OqykTEVT8nrxqJGCf13akGAg1Zr5u7Vy07p7zrp5"
    b"EwgeKyDB4BLoR7HIPmr0ozaOHzAT2f35HSC1C13LtUet5zfsr75e++oOE7O9OG+dumVdOrF29aJ971f7q9/WvnpkPXgIu0DhwCpd"
    b"wDcQPPy7Pb2DSdG6fdI++6i59D3s0j4zZy2dXbsyjz/vX0KsB/sOHR7I9R3cJ1iXzx7S4NXSaqmgHNsJdqwWejszmUznH2tgqfoH"
    b"Fa1X4ij27c79eWAXYNnuDQAbeskO9LB0eUYKaErjyTISTJi+gT41nl23f7rFCINt8PEL89bSRevZrPX8R9hIY/nbxvJj68FZZDFb"
    b"Yk/f/v27+vrf5SvHtyfJtiTZkQg+pnTEdyRJT5JsT8T2DvTtHjh0GMaOSx8YSqWjb1QpmVKWSPo4siDdnercmspIU66raN1/bD/8"
    b"LG1duwFqZd3GPVj3n66tniP/fpjQU2UvULj26XNrZp6MfqKWSevUQ+vhWU7IehdMEqkvj+6hY6DEzkCEAU6XTNWsAz1A0LCsFqqg"
    b"cCVizc03V6atU19b909YT56AoSLrGFl1kx6NyKrdA/25g4cG9uz7iyNiA2TsoklL7i7XTs6DVrRW79mXHjSeLKxNT+OObi7BT8Dc"
    b"/P68x/lD73/w3m7cUBcfQD6/v2cPjGRSXdvQdZw7g85m4ab1/Wlm1GyR5vIFMP7mygXr7uXmD18xD+zg3t/3Ya6/r3/vQO7Ikf2A"
    b"q3NrJgYL/NtAbv++A/vwBICBPfv2Hxk4lHuv78AAZSk9UqS8JhsGsqv5cNm6cRp5KVcUGUdw+TNLOKLJjKWt+3dbd6ZxpK7IFQrz"
    b"9FFjeVVKMmSaYpoKG7/7lX1/HiGH6/jbXjgPJoS/DTixcGTt1hIdiU3BKXVgwEd/D9lMunrA/8eAQYcHerpzhwZguKKgxyhDmBCv"
    b"SPGd2cG+jr/KHZ9kOv5lS3roePdUYnNocOtUb++kf6hrqjexE07U3P7dB/r+EoH5b1TYO0HaWqEoH/sIHul6MQ3EA9g+mHhgYPe+"
    b"voiJH6VgfXClk+iCd06OaLVJuaZOgmOdNI3Jol6bnCjCf8pwcbLYXZsslguJt1ysG8ne/YfTu/sO73Vd4lVww62lH8FVtT5ftc/f"
    b"RWt+Mr+2ON36x6etXx8wxYjlDh85NNB3oC09lJbgWngozJ0EqwSfApGaezQQ+/J9GIIjAH3gzG+N1SvMFzeeLFkLJ6yzP6fBHUHk"
    b"h3oHDiKHEUa0dP42+VEqAZ8M8STz5JPMk08yTz7JPPkk8+SJj7j7BI6XPGJjuTG9qOTycn5MQb2diuXKmlwXB2KxgjJCTOWYGa/J"
    b"WlVJsMCqopjVSolIElFHCH1AVIO8p0PEoGiGQgyzwuFT8FUtxxMcU1keVXL6iA9ZkW2xKJv5MeStsXlwS8fQzo8KW1CrX70EC+FK"
    b"gEUtmfFiarSiV8vxTCKBM4sMOiOSDaoX70ySEgUoMYBOTqCmGmaQQD6NEzECdKglA+LAvMLAknRWgiEaHOKYWEgUxBU5vaDmTf48"
    b"uF77ScAAYY4bKjt/NBwsAFMwkk9h+GBwQlwwHja7AaAfAacClCAwwjH7iWKDfCuME3ymh4fxBYLIHNIUh/gxScYUGSJsoxcFm6T5"
    b"hV41ezu38a3xx7AN58iCZZ1Bnz7wQbakUaY6xXKRFKzoX4x/euvxzySRNU2fyFWUgloB4Rm9RyoOw3wMLsimDCt4IoYVU3RTXBvb"
    b"s5ZP5cxBBdRNOijIX1ZhQ+7cuCSkmiyQtxd/aD2/iKf/4px9aRYO/fff46kMZzdi5AyH3CSOaU8SJScXGa85f9kI0MO/6BWHMuBd"
    b"pQ4PxDQvBT8UDASovAGeLcm35ApW2mRgkIZZBHyW05uMnZsMiWwicfRpSAYSQxfg7EKUgAERUWlJOMA3BCyij0HayCok/iVqr49z"
    b"P4BzEpjSoKlvzWRCah8/Ui8rNANKkj+hYdDviQh0e2RQMHeYi0wfD5jLS4QG6SBhERsLJNuKqqAg2TmWivv8Rl5T5BJzlEZ1mLpJ"
    b"5h6TondOiErFpoBE8Yd33KdGqprGnC2FCDseZHFY5/lDRltquKebEcuRvELrRczuVjH/z2m1gl71bXXDhg1eLAtgENS/X1KAjRR0"
    b"C03FINTs7CHjSj0NwTp8U2tYV0j37+pPH3y3//B2wEFx6RV1VC3JGnBOYJPIJQcCDiq5YhoTqjkWl9hKUpg1DrSIgSf7L4f1sRJs"
    b"CPdO3bNf5M6cwZ7sUCKocu60SEftWw7/gDuAn1M3mO3sGUpx45VoHUsSFqgJkJ092a6tIVgkAow/zqES5B2Itbcy3wsruajyrNjT"
    b"i/JIlZSJODxM0h8H3t8Nweiu/iQs5y0NEYeKik1LPnE2O8WVI+7uOMFQDGt6fjxnqJ8Ip1hFMaqaiS4MMaW4VnKyk0RBqzZ6pYoC"
    b"z/PgVNyIROAuw+FTAQxVpUQkpxn0KzS+DNF/LEo8TP1VI4cr5MCj+pTfpyfuGR50wvRLPGT4oUM6ZUAkV1SoG2Q7SvKMCwQqlwpk"
    b"WNc1fnaDsExg7zotmflEdy+GaiqhvXC1bbfVEDZ64OsGyjL+6h2nELQkw+7AxUkgVzi5lUrc51oZNsgyvdocQuMw6HeBi1qo3CW8"
    b"LdEUJUS04wWRb26ew2NXkbpE0M0hNjfeA6aO9WYEfzezYt172pr+lCXP6OsQnuVHPK92XJo6wuaTd8i2ECMliY4A1REej5lG2OkA"
    b"dMJDTWE8xAxVxLHDIV9tcImAMniMxYVDW4BBHprAHnuJx2QkABcWyUWPhIAJ8jYk5z3t+OGzKuYXcRZ1ioPZbEdne9fY3ldTDJ0v"
    b"ddSobEii58cgChLJDJO6Xh8KQ2EnOlw3FblSkevtHakwSS44XnMQOCBuIkPepo8DTGVKpDlzACI7FPbDSAREnAiTeAN37ERFPsNh"
    b"yLnlkC2kM8HyD0GZGAjPPdbloj3GM1sdUUuFkMH7ohGEgHAEK4bLC7xETYuCNAInjSd37TNfWCeXUEfTmEsDcFpTS+NpGtrCqGDF"
    b"zBzWlwty5RgBfUL1pf4c6+9ginwZWk2ClcQzC091ipYG1T6NwaQ6Ug2Z0/B5UT9fWICO+5FcLwfs1rWakmNeelgv1D3u0U+PhRyU"
    b"NhqwRs8WB3lSDlpnZlrfPmUh3tkvOSc5zNYECRcLuXP0gsLG6jyyqFfFmntj9UrjyWkeswIRJ+wvT/oDRY67K0Hsywv49IND+32U"
    b"42YcX0o3JooPByL1iVoxHLAq8AkzGwR0JuJ3X6hxXHrdRN4jxPkb0aslBHJlxab5gWBxCudfIEgrBVlnkYBGOW6a5iARd+dVe31a"
    b"TU95d8IgOkkR0ueN8CHOSET5o7D3ZP4dJ7w86GUuMgeZjAOOztx9vJE0Vi5bM7P2mTm/AoHdw5f2AhNPjHC25C6aRNOku++l4Y9f"
    b"VK99BPwusfTvEk+/XkwdHVevU/M8WVkzi9bSJdoGQRmx+q59+T7k5RPsRGovMATpFdTB1RhNNtVSR6ewa3W0pFcUKbxZQIHxNFVV"
    b"eYId8xh5ZiJs7U1E+0rx4qovF+zvJtzXF/DvIuSAe+U/XR/iVpjB77GAQJ5I8p9qoVdsCnqHk33qlNgRsk+vWLO8/G/dXIIR69wC"
    b"q9zAaYKGf3KpuXjTuncDz4kXK9cc9GRteo5Pu3LnxcrsNt5zJmnSI/aJsT8eCAGAzLZhq1zBljvkL5uMTcYf3Q7/pgKtprmt0qQ/"
    b"Qfy4qpsK274hjyi9G/4gxRObNyQ8biTcaKICSgtKVZFLo0pcbKUJUkRZA9g7QWXGqmnK0BSlHMfnm4mv85Z4icGF67Nsq16J1ten"
    b"9Aq1XZmw6Rll1EGzauRYGRF7chlqjfgID+4oj0OjkALz/ELs4kxpp/FsFkXOf7yBAdB5r2sCwWgVgt+iUlDlQCYVkXRHplleyu1L"
    b"aZ0OXMqARAJy2pfk4Yg2QS/UJIS0GRyGIhcD62IQ/fjn5vJZ9MjYN0sXywXsUzt2ccY+fxcvOF250/p8lV1TsU/jbQG8brDIO7Vh"
    b"23nTXbqNvTfeZjd4WL1agbjdt0s0dX7N5Crv+/kvgng3RvhtMHpQ8csgrPvo3eTpIfb8N+38xmvsfR1FFbbLl5VUsPGCeFD3hf6k"
    b"w0F8FqYB+ycxHk3Rfqh1bt46e7mxdKLx9CaIuoW3mq6uXb+BPVpPIawfzjdWL7B7b+yGkLV6wWutigINmQElkDMooIxcfNj1jMOm"
    b"lVKhV3KslTY9cyx2BHfLWqO8bfHuwIe8zM5mOV0LnIIuROijUmfm4vI6GAwUSWNfBzND4FCpB8V/4mHWcTiemPMeC/ZypJJcg7P6"
    b"uGTq40oJO/7SFCcIrxwo2M4ZZLNGVM1k7TPe1UGXr5pKEX2+0+r0ui44AkldNljPELJUnBxKUlkLpwTBUtXXJ0Fghtmsl/HcwTIy"
    b"b9rxvgTlagAONdBHRiR+Uy04eRnOH3TXEOoxnCHOhb/jLkwWp0PG7K2XDaGiw0OJKbFzZPq6fgG6mXJIQomFtqIFeQg5fJJQQwM5"
    b"iNdHUojSiAf2TvNuiqZGp9doAYDSeyxBR47hiKOhbrYP4VtZU4G8pMS64bWhaLwo+DgKNYU3IWEq7xUbidBxy8bDJxzbqsvpyBNQ"
    b"AszAaNx99HMuCfxoA6GWVHrJRWrznJIHAIPHJWoa7AYbFkdqzFKGyBbnYY2P1qY8rrLtDYWxT/lqJ2y3fi5wYxsEzRrCdigFifmi"
    b"7uPurSCumUABnwZj/JvbGeYw3iqCnxl0fQyuFRccCezPf+0nydf31XR4GO45xFxNLzh6JzobetMuR2/XRTudGiqP4HJe28Osx7vQ"
    b"RVLMwOIOWs/8ahyvb4vH2WpZNnnKu4GiliBdKFCqkk4UqhRyeDeFL6vRHbUlP8azRjrF17fGAZ4d8mfOjRcXnGWL/LvX03bqlj5q"
    b"wsVrTS2qJm9xi3TBKDhX4H3G18B5ZZPbwZdxK+p04G1f5uoAeRffItrDfE95vVoKE+g+eSMig7gZsWOy4Rv1Q73DodpDYEDjQ0El"
    b"QOWyhcQ7ncqThoWnd3o5E9htokT0/k3dpK1mb990RCgX4IIOlDdDVAOZJmQ0n2dP6eKZ1+KXuIoXBYb2i0u5oEIFks/0S5DvhAsO"
    b"cIYnxCnvOrCYu5mza4vHQoenoojoBJGluN4gs6IhbjyBcaZFzkP6S4BghjBEuLiEJ4x+fEK/+eYYfIphtrtCAw5jVK/U4zRqKI8m"
    b"CQ8Es1GmXh7l+uFFKKaTc/OICn5nwy1bxzO5nmtwaCpJPE/AFgWc/IvfebLBqCtY7i0fcN9C8FPGq6d4j46uQPsHRXa6du6QpoIN"
    b"BzFMEVoM9FJcrxgde+FHLBg3UJVj3/4AYbasaVKo2A2UDvJjzbsBF2IRPZucU4lfRnJYxR29JtdpXCN2c8qYqvsPK6UEduyGT86t"
    b"RRY3bRRzeUPBqgUFT2GZPS69Jfm2iADoOH2xLYUfxEdbSGd26FVRLSXQfUFlk/EWT0EEXFlANpRIBm7QBNfxn4Wwk9RRXcVmKeD3"
    b"mtOmrGpxtWAEiwfeiVyAGIWeuJABVcua4ju8C5SX8DEkHJsCb0FAyFkAEDTGs4qaWgj1Tmtq4RUsEqMTqgE5tg8anlD1htGphNin"
    b"eklCw6KA9SQ0qFAsmfK8IgRNmF3msPqTYwDCavAUjW4cKGKWlGRBJp3PI30kaZxaQxQu7/IlxsSGyzi94K1P7+xi3C55Af9bbwV0"
    b"U7yqyfbBb636N81qGgYrENed+5Rhl++HHQxFy8fFUN4YVIcoDeRtehzQMe6hsKFPO5lZUp0KoaHBZJJUkWlKqVpUKmD88TYsQCwB"
    b"DvizFyEHA24F0jKYHZGo0eg3ybfqp4JvP8DAsIIxuEgVi1Qz79KF68EYCrZdtsuoNeHJOtHTzJOrkoibJ97ov0LP2I1M+kxiJS5e"
    b"haYsoi15fzaELHYcmXt9ZPCtjUMocSKx/DewExSCM8e95sEtaTCg7HhAUCkzx0bXazcBmRaAx6U8cPBczrowKTqN0Lwkgte8aBoP"
    b"pz1j+4Tr19zKT5vAgAts4k1iANH7MTJYWgbrAvBE+FznaZr2f5+kCUwM+zyarIV8HtZNnETy5dFYMG8LHvXUrWFrw3/xwD4zx7SV"
    b"vYVjzZ6wf/2UlZNfrMwK7yk2nt+j76c5NxI6Il7vI1Fv9Lnv8s3hHYSyWtjB3y5jtVtr9oHLJPG9vrT7Ap+zyDVr5k7r0Xdr09PW"
    b"tRvWwk13cXY7jK3Wen7ZfrTcvD6NtdLVL5rLi/ylS4dqr7pOp7OLEQs37a8fN5ZuN5evuIV29s6LW1l3EazvZcl/Tv/D2/F2vmPe"
    b"ATu5RKlwkEbcxfWHLo7koq7lhizkuESr1qDhGffkoIcI6xzBL9TMuK9/lJiKxZw2ceRFO+fVtZlZe/Ena/GB0OIPXjNyCBN0n+/G"
    b"uSImXFtygUVTcsEDV81D7FEKDtnhN9XYOy86Nq6F2k+gLO29zUMN209N+6o0oF0X290K9fq4rwYaJxGcpK9PMbvJMlNCDeuh/zpK"
    b"9q8k0k7izBqsEzNhQ7EWl+wr931Xhp3un3BvBL1VmQWsodc1g3dO3Pleu9nZThKRRN2GoFPCJ/RwRZHHgwFqNLiwru+2t6Kpwd5b"
    b"BHPbzxYju40+B5Bl5o3830b/3RGQQuPJRfvyfdav4b2bBw9df+M6mzdm/Z8Hdv1/8Z6VYsT2UgRT2zE21nZtwSoHHXBaw0Vr3kL8"
    b"r5wmXQSJWOwV5uiSQZt3r7bJGK0v8//HQZx9OAVg9p7WexChxQ1FG4m4kPg/Nxd+cv8fGPxKBu2NliD6xjlOjcRrsbEkWhtJBesY"
    b"lGABhfEnTOv26JWi7OCK7HCGen8ejqJcqsoaxdM/puTH22yDX2N3ZmEhvB8iZkim+bqsJh+eSHuIwmYSfiRsYQFTNAZWdPemOnUm"
    b"Pw1u0YkREyg++VqGbcpU3gosVfbj9/J/3/1btzbgzWYBp382DYI/rqr5cVyyV+qMeG0mEC97CFmWGWC5Jo8iURA4quU98COCOhrx"
    b"qeLGND0vawcr+rE6R0OLQm1ebhLYAT5TrwdFhJcu/hdhGZkp"
)
_EMBED['sj'] = ('搜剧Ai_酒亓.py',
    b"eNrtPGt3E0eW3/Urak0m3Q2yLGNjwImS9TBOwiYQTuzMZNd4ddpSSe5Y6m66W2DHx+cQCA9nIbAZyEyAnQyThJAEAjObh9c4yTnD"
    b"TxlLsj/xF/bequru6pdsyGR3P6xzDpKqbt26dd+3HtlB+nf2k4pVNcz6KGl5tf592JLr6+vrXL7RXv5s7OCjtfOu1XqzNThUqFjN"
    b"R2vLk7/+pTU/8IJl1g8ZpH3xaueDc+sPvu1ceh/+/dvJU7lc98sPu6f+q/P7e+Q1qlc8hNm8+U179Ur3yu1Haxc6V+93Ln7VPnN7"
    b"45v77ZVb5KVDYwdI9+4P7csXu9feIf808eph0nnv0/aljx+tXcsR8uL4JCEDxwcHapRWB2atJiWZf5u3PsCpzp9tX1iVh8441gmX"
    b"DlR0T29Y9edtvU6fbhhNw3t6zjCrTx+Doe3zv9u4eZsMEFh49+s/yaPFsIFnjepzGRNv3LvVOX0GeNW+/CWwbfP6WeJZc9QEfmVh"
    b"GqC24VpV6j5v1Wou9ThBhI+GJcBC5KF2Q1+Y0StzAw51rcZxOvAsm0AmqPP+3c6VH7qrP258d48vBxAceXViMhVBf8Mw6fPHDXqi"
    b"BIK1UVIbn33c+cNlgh1ly/YMy3TJ5rkLKBYxaHRggHQ/vQ1CZgIDCaH4+ideGtu9Z0R1acWhXp70HRqffOnVXx01bd2bff5YizoL"
    b"R03PaFLX05v2UdO0zArt00AZcqAEZL5fN/qbFpDSHwCBIKRmNiDa5Bp1U/daDiXrK8vrK1+0P/katQ80N2c0bcvxyKzuzjaMmeBn"
    b"U6/43990LdP/brn+N4f639yFoBEpytUcq0laTgPQFWzdcSkRvcdalkfzpGX6X5zGm5Zhsi8MMBciBz64npvL7SCdG8vrq9c7X621"
    b"715GnQHlWblDfmnQAy3jFQo603n3XXJkwZu1TBLYxMbaSvvcavfqt+TgxKv9+/bt2d8/iBIDLq6v3AUr7Nw4vfHVu+urp7p/WkNW"
    b"7ODjEMHR1hvwRza+X+7+8DlYZvfrK2Rs4sBBsO4LgAIGtD+83Tn53ubqGvzcPP395ql3AKx9GVCfXF/5S/vu79pnTqPxLp9cf/Ap"
    b"kldtNW2XtK+vtr+61jl/mVDTBWGUdbdiGKVJp0WRBM9ZGM2hapYtx6gbZpmPKjEBFNiPHOuv0hrhY8uuXqMcTrVm3syTnbpTd+Fj"
    b"59wJ/KZxhPjHG6YUeWplGrDj9AEUaGTLMaMUpGPmpCTIKJQ9q6ov8HYZu1EjpuWROvV0z3PUcE15oshjlDx5QW+4VCI9hAWEiRlz"
    b"dL5CbY+Msw8wQz7Q1l1gF+hmAe2qoNs2NauqUigoGtfQGd2lBdc2qtTxFXSC/crlJg5OjsNUyqzn2S5YseTTFdAU8NmbD/7QXr7Y"
    b"/fJe9+ad7ne3QSdAc7r3vwczb987u/nv90FTK7Mtc84d4BZY0Z1qv9Nihk02Pr6JiuY6pL2ysnnuEjq+ifEDr4H7KpEZpTa0v7p3"
    b"SNf36iPDu0d2F4cqVUoHaW1w78zQYHVoZi/V91V2D9WGK3v2V0Z260P6Pl0vwihK99C9+6tK7vUxQKQqh6y3jEZDH9hTKBL1N+C8"
    b"wbGTw5NksFgoPkOgYWT4GTI/MqyRMdtu0N/QmZcNb2DP0N7C0AhRBP8V9eWXJg+9kgdPN0fJi7QyZ2nkwCywkA4MDg0XivgfmdBr"
    b"umOIscDiI2MvjpcnDv4L8nGomBs/UpZbdheLuVcOHh4vH3lt/IWDbyCvN8+8v776279+p+RePnj4VxPQNKUqjHegEUr3yjft7/+s"
    b"aHlYlUsdg7qideOzsxAEeIduAnOxvf3u7c7al9AYqBD0Hgf6qLfAxj1Y21he5YOqVqXVpKanO7xr9Yv291e7y+fEXLOgF+Wqozd1"
    b"1vvRXTbbdC6XqzRAw4TKqPwDdDYwUMM0PPDxjVqe0HkPdK/U1yfpNJiD4RomuG9w1iqHyJOqUfEkIPzjXcAO7BOAWgBBG+mIXM/R"
    b"iA7jeEMBfhu2GkMdOJzU+ZjVNSy96iZm5XBpVpeKaXFJotelGeuToJBthaBDfLGcBMis5XoAgOYa7agaDq145eZQax9alGU1VAln"
    b"AZwQCD6EUTQtOt52rHnQMRibGCa6FA0JOmyZVBYpergIAhSBJJ4ENvQwqGkoryhfYnQsctBRmaAp3jadF54qvTfOM6qDpjKUkfmU"
    b"18Gu+sfqYApRPJzQFvTyTrbw18fy0dFjFdQDGKmAp20YkLuBTgygDuWJB4gwo8JQv3Ngp5I6tP8V3ay3INdEHG/N9h84nH9r9plj"
    b"pWJhf3zAa7RGHeoAIHPUu4gyEAd5lcUvARH2xXjhUtcFMoEXfsJRmOBNqpYK6XOv0LKruifkKdo0WRFk6aXI1UcnICLoRJsWuhIQ"
    b"wGG9ybslLRGxWvGLj79+x32oKsKVpnAUO0h/8EfaH612P3lPauEw/wgK6hmVJoU0qhomGTVjvty03jRm9Dmqohil6Zl1QCTHZlQJ"
    b"RdESpoDt+EU3F9TKLPhEaKpBG/+uPDz98NTDTx5++vDWw88efv7wthKzAbFCN5fpsYBAij7CLVATKjOqKg1Yh9k/qGiFKuUtrFKT"
    b"iOvtuRJzwlqQfOVoa5gWiwp5toTkw7/Qsr9WqynSihg56YtgXbnELJz7LJbEmV9pUN1UKw2XW1CM9dBeSJFPQjuIUsAkW0VRuRok"
    b"PA2IS5qkXWUsDkSk4iTkCaZM5WNy+uj54jZMT8UkpoD/qBrZCdlEsSg5UF5+lKBUKLQc8H9WUx0c0cBK5iWjarp1AKkpi3xGMAAb"
    b"oqi2dNRcFHPjV4/9yxAuKYGE4/IE+gEXViwFk55QeSKVxynyfllTcGd1qLkYFVWjDpauJji1qKSVVuBCPExR4/UVtLPPfCLsKWl1"
    b"F7pUo74kcV14nDK6yBTu5yFqVRdKGGDyrKyyWl5pcI8kkdCRM7fBxRhlJ0elZZsP6HZ0BCmBXmMVrCTjuZhwSjlgmRAYvP7JBZuy"
    b"EiLh85XEYCeMpoHzg+itCg/OlyxmKInPcOHiM8nsrD9wp3oprBtUZCbPILRYGpNISDKoxSj4WMQ+psOJpxJAQgGdcssto9qT50pk"
    b"uFjcemhCxgJISucQdYXLMOYkQdEdCpEa9Ft7EvpD9QZ2yarNWeZh4l4akpQYXaeBnhM8RZ2qTX1eHRRwWsyPokgDZY9Yj/Li+KQS"
    b"13XBRjbKcFkUQhLTZM3oR8D4YAOEPUie5fQkRzI36DYotdViYTjpUGRzR2VPMgTV8udjC7Njear/i9yJZid8XzGenfBwCBW0YJ7h"
    b"RSspJF/Ksg0vtZJKs5bjBmYPhseTXKPKs1v/N5aMuumV/XYl9GsmJGQB23mk9kd5htegUUSm5TT1hvEWrZZFbyJXQkpEtoS4tybd"
    b"pbqLe44h+aKFTz01HYNk1DKAqeI0z1E5gkSN4gMJLjIfKddeDm3qzpybsXzRy6ngyGTyyg19hjZ8fibVIprHH7eqyP1RZE8+2YWc"
    b"wkgMHym9tlGBTp8utEDqlFtOMHnKEJ/4UX+RKTALVMfagyVDAjdrSiw4bFUiexE+It2hul9rxZjIunoMbYBfyBja8OuoXjNXPAvX"
    b"oORFdhhOjD2BCmlTo4O7p9Mw8Oo5A4nfKeMZSaDxIH3wJZjEAbWmQ2UEw6l0iDiWwYsqdSuOwYJWCjuWYt7FFe4FnZ3kOzDxAOwU"
    b"LWhqGr/K2SNz1R76ahXH8XkZtoD2qC0D1aHloE8zvIRfRhg0S/ic8m1gmrs5k5GSdLfYWtCrVTUyRkvAwWr8zVAAStgfdIdcwfMj"
    b"kewJ1tSMhkflrYpI+AmCvhI5gpKsnBU61EUXTptuhK3prHVpJcZbaGGHLRnsZaxnFFVSZBFnNLKUASQZipplmNLeOA9q4L1jji+Y"
    b"KeHaeXVSFZVTAOeHEwafkD1rTSGHc86X3SI3H+YbFeT0qALhGCbLRw2LYVuKThKqbMbSt1TRJ1fTx1FVNgvqSarC4irmKKRPLKDg"
    b"jGzjOKYNPbiGp5mMawxLhGsM5VIiRjNiUiPzosJmgqGoxkrDcD3/O9ShOBuetv7xbX5W2/nL+xs/Xmlf/0Pn6krnt9eUpVwmusBg"
    b"fJyMBslzQdVF65azELVTDxXBrvsG6+9BywV9oJcezzzANfrbxAEQnv0ClMg/sfS36wg7KOcv3JIRtGK1TE+YM/7O5SJ6jdvQuuO5"
    b"JwxvVhVKG9/1ZFQB6NSe0ensPHdrR/PE/sPfwEszWGARFsguZ1hPHyDgRrOVOmJhGHoq6RYwA6nAXKRHZvVgj611VPCQm2ky4CYg"
    b"MjxFic3izbI9mow7AaVF/HeJn8SXFoPjnSUl7tHYLIm1Mfy7SkRh1wpKaIjsXFjFnxAK9BotKTGJpitBSuGXwmAW1eN8xHOVQDPg"
    b"t2HqYbIgpbxxtjPDwPIHlgfz18Vuvu6Wm5YjUi+VU4EOMoAwwQ7LNsvONMH2qKEEDkA2d7B+m++M44f4xUgRTex7ylYUkw36M2py"
    b"ajR0dBYIERr3sz/JlUDu6lRmo46E+cZjLaMyh/6kpAzKFrsd9zB3QrgZwJTlZoR7nTuR4Vtld9qbEUtbJCap2nystCg074TQu74+"
    b"benp3koec4A9le0xFO3nVLL/bR2LlPobn/9n5/SZ9FLfv+wjdBBrv3hSTtllgCnKnDyNuXh/fODi48etfmXLTkiF48YLQniymyU0"
    b"gbTcQ3hs1ViQoyX40mCNZc5JNgAZBeRLNsLvNMFAvyvoOTFrQL4p+p8VEyDVQdOeYnxXEJUjS/P9O1VC4RlnA40PLlkp29hnrSni"
    b"KlZpkX8GRiKf9S/FHDi7ExEXHBL8dxScnNrjdMnQkwypwHRx3KmyMVGqBbN3cQGlAIjppJXEtSSxxhQ90mIGnme3Z7St6N+6PmVs"
    b"hiXGjv8tlESUi4liBGAyc/nUCilI7mFojIth5Ul7151ldqmOJeG+D2D0Sazo6+vjF/C6d+6sr5zcvH62828/ts/f7353DS/04W27"
    b"8+3LFzofnupeud35YI2wDaGGvlDGyz+P1pb/dvIUXn/bRnqZuEwYpiosfWaUhQlLuDS+ACaViDgsO75fIF8izMhLk9ucAJ+6z5kp"
    b"mpQ9S8Dhb9m4jDvS7lzQJ9q2cgryENuxjuONGF5QRdEFUoiXyrhEJBGNm30RlSTnY3KRvN3XKRyRUCsOEmpWlXq60YimOEZVPujk"
    b"O8JSLhz1QACcJyoGTtDJlg31O3dGRryOPh7UV9CFO64ZuQ+/wdNzdGbCdDxeYCQzpqXcdlTcDwuhZoeRQUnZrGaoxG51qMWi9tlG"
    b"EidqYp4DZNXEsVjP6Q5SgzApSNobB5WdCKAAGUwJN8fjCqJlyZFknmJ9aRoXWrOy+eD3G19c5K5GmU6xd/lu2y5sZ3aPn4E6T4fr"
    b"qztWy07xE+Us5bexgovCB/s61Xko9m3m8M1Wkzp4rwRTirQDmuReFrVjZSygrCngYxcBMeaiS+BplZRaDgjyDbHWt8h3nZ5apHbA"
    b"8qW+qLHzRQf3MneI/V+Gyb+eEO5FPdGxgLywhJZqmQcGUp6+nSMD6TggHPkEW//h4CfY/JdCyTa2/8NTjnQckSOclAzYseoQC90y"
    b"3jh5vGMGaZE/5aAhRPNTjhpCLD/psEEipudxQ6hmQQAEap566ilBD7f0zAGohRF4bkFa2u22hNMFLNNpVRh/BbHd62DMowIdmDYk"
    b"L6KhBWBPJJmVbCcMY/ItGJZSlWGyORpuXuIP8O7U9mZLxWjWF31bsXHr7S0ebZDOpeud85e7Nz5q37vVvnG//R8nH61daF+6t8Eu"
    b"7gOC9tmLAANJZPvPn8SyQhEOOEHMGJAk8hwZSg1yUtYQCbbh4b+yvcclkPovKnxWtoePX6TtaLYuuTbFBiVeLGF35Ag37baqBI9I"
    b"eh2cS6sDqYr0BAf1kLQ0G/RH9h5DQWZd+xNXGiIaAlimsAiLDp8WyoIRKpEDwhD5IgbgYYoslE1k3XlSa+h1+QpGg9X/sqEzCHlJ"
    b"2CCvSQr7sSUJbPjByI9ATifYhUJgAd7iBQMrF/xHRqmVsSUkl0hlGKr0lGwpvpbRRDohSpUUJP8DBcU2igpFST2Y4oSVUhYVLztt"
    b"L+jeQSAH7dxY7lw41/7qGs/uHq1da7/zRfvM+e71rzdPfkzwtji6jzPfdu7c9NvsYXzsc+Nk+4cLneWLUG9u3jgJfkXUp9fewTdg"
    b"22OqsKswffWdbbxOihsTv0fOd4Z8dgFMGffS+aGFwi66Z17wkRnxs9K4LQr8W0c4O+TtofmiSlEndiYNQsYqDjcK7RfgR+TeKmaf"
    b"QSm1xQY0A84oX9gDNXDGxbB86b5zs3P1PAiYR1EeXJSIVTGMW3Ih4vBQxS10e62GJzYXcj9xm4JhSSvnfJcSjyXxvYg4o0T3Fqwa"
    b"BFbxrEW6p08UfmESE2180RK5Qi8VfVzNpJizg4AZdi4sc1+6+fYKGB38u75ycX3lLsbwC8ubfzzbXr208fkt6ALjbJ+/zzeFCDKd"
    b"cPmEWm447PWICNFBWIgGhPDmAtiWgbf0mV9mg6dhSbKH9rkJTLL8W3V8ltgVq6SzlkwunCjGXv3E9uwOADMDbcSfxhxENNIqaQUj"
    b"S4NKOENaEN5ycpaFAEQCs+xTYgGff2zn0i5HEkf/GI4ouq0qVH07g/8umr+1MwCMcu4c6eOuECFGU7I0/Jbh+hoWqhVbJXsaoDyv"
    b"aOByC9COF8JldkBTAYp1wYgCfznFd+v8d0/So6pt+FHOImGAjjW/wJb4mIxKQwn/bsvR8IyQzZzGwMRdanwz6isqmNARHPk6mOFj"
    b"3pXGjDT+PERZRORLT0OffxwpJKfJh5JYyZYY59OquRt3Op9/tP7g4+7ls6knaw2rojeOSOsF1unNnpdpGUSvsmBquDiMJ37BIy/Q"
    b"9BlF2hazkWahiAyb2IfB1wOZBYPsEfgddebvpPGs3tBSzPXJqITxgtD0XEk2y+bQkUBb0xF4bo/hnpsyfCs6e9XlEoPA/aW80cLY"
    b"0Tv1cbcq+QBOQS/OjoO2eDKF04pX/mr0Xdy2USSfqvAn2mgkI8Ox3VC2V45etqSQnUTtx9jkauQXZDh2fYRW8DkoQ1EAbrFH5DMj"
    b"w+IRBCAqiOcPqtKPDnsXMCxoKWMLhLHsl2XxRQJc9o16Wtmm02Av2dMfjqH0fWVMc2DhG6GkC8wl3vX47yqneUCIAxRsy1b9h555"
    b"tpug9Xp2kvqEhnnmzKczu4uP6Umn9hR3b2XW8Zc0/8Den6eji8H2RM0ePpbI9l7T5GIhJBFw5ePc5FEA2/EBjcI5+ThscdXkISHb"
    b"kJETlh3jb0z2v9H/8vg/i+sHGQCHxo6kJUVir8mBMa0Z1VFef+1gqU+d+te+6V1an4K3L5szVZ00oR5iXb9w+xSwPPH/9lBxuXkC"
    b"Lhs3K9VBTcszjPF8ThAeJBNJInvQFp0riV46eI52+lIHdchHH7EdN6s4pEELTZvWMdQAwFFT7Lzi6674c0SpSPX9+/9bZJrZZJoa"
    b"NvgL4ze3xTtDKVNgOe9A096N65UsT+K+4f4agV7AJzfpebGggP1vATDPQKXz81kWm0TexWYEBRiOtMpvZ5u62dIbbL4Ds7Qyl/FE"
    b"m/0PTeRDaMBlLcSBEwKLiKrSsFy67USTxYz/BiMSfH4="
)
_EMBED['xg'] = ('星光影库-TVBox.py',
    b"eNrtfWt33MaR6Pf5FTiSKADUcB4UJVtjjXRpmZZ1JVmyRDnJHY3ngDMgCXNmAAMYPixyj3Zj2ZJt+ZE4Xj90nWTXj2wS23Jyk8iS"
    b"ZZ+zPyXhkNKn7E+4VdUNoBvoGY5s5ew591ytNwM0uqurqqurqqurm7u1ifEJrem2nO5CReuF8xOPYklut7b13i/7V671737Vv/1z"
    b"zVhdWlvquMuOXWi6HVP76+V3tNlnH3dXtaL2pNtdOO1o3lq46Ha1wHNatg/tm1Zotd0FraIV7VWv7fp2UfOsBVszWvBlYlyzwtAP"
    b"TE1r2aHltLEedVA83Os5rSNFAOG1rbU5q7kEiDWhoxd6lr+kWV23u9Zxe4HW89vaxBGt7Tattub57uqaZniWb7Xbdlvzre6CHeS1"
    b"f5osrZq5nNPxXD/Ung/cbvTs29FT6HSS50XftpAbUQH00nbmCgA4sHPzvtsBbnWbPd+3u2Fhvhf2fDvQeN1ZanzWddszq3azF7p+"
    b"XluxnJC1WwxDrxDY/rLtRw0etwL7qdnZs+fsF3p2ED5ldVttGxrNRljgx/PUJJfgTXUDBnQOIBQY0yOg59kQ5B6fPj+jVTUd+w0q"
    b"xaI0hnruxOnjjXQVpwMjFBTCTmuu4PoLei53YRq+G/pp90Wn3baKBwolzfiR0225K4H29KxWLhVKj2lQcHDqMW314JSpTXte2/6R"
    b"PXfSCYsH9j9S2H9Q03Ma/dONk0/Nnj6V19rOkq0dt5tLrqkdWwQy7GJ5f7lQwv/Tzlvzlu/wtroJGDQuHPvhSKj6jhBD3HrNiWbb"
    b"7bUmWr6zbBcnCwcKk6UYuxLiNvXooYOF8sGSNtO2m6HvdovlRwv7oeLUxNzUI49OHSpDPRl/qYtji1a3a7eLXnNpqeGGi7bfaC4y"
    b"Cp85+Y+nkObPfxuRuQvHGtNnT4jS5jUnLM8p9JqFJvRSJMwIMT33zMl0Zfow4TULREa2Re7s9HGU5cmp3OyJ0zNnLszCS/lAbubH"
    b"Z6effqLx+IUnjs9g0aHcqRPnZxuzs6ewckkb1w6WcmdPTf8kKpoq5XLPnnhi5kzjHMLzabp4Tts2fP1iweh4U+udpeX1MFiHybQ+"
    b"315et5ad9ZXO8npnanl9xZ7rrPud5bn1jrcA/2/D/0xCXSdw10NvfX5q2dyj5xHqCTN3/qnpczOZboiZPiP8KFBuHK0QjReBUxeR"
    b"8KBYK00csiZenJ74X/V9657Vvci4ovhqQuuLR2vP7bqoHz5yMaiPm0dR4o4piEt3YkhwoBUMSrZVpvdMs7M/ekLRrnZ0bx1w81Za"
    b"QEAQrLh+y6yKbS9NbWDr3LHp2fPQuEZsMXTSYMBB/b9++cbvte13/gQmCl/5k5nn9cJlVunnt7X+tc/uf/gyr3Tvs5fhPalndUH7"
    b"s6qv39L6r/5m65vf4St/iusFi+4K7/ZjbfvON/eu3SaI7Cmu1nKbHNh1bfv2b/t3f7F97RWqGL9A3Xoud3zm6XMzRBh2tXn3BnX6"
    b"7g1EDqtf/Wrrp1fo6bO3+1/fwaetf/n99rtv09NPX936lw/o66tfbt/9LbW99hlvAfC236EW/U9eobbJ/ISyl392//3/IChX39u8"
    b"fY2e/vmtrcvvUosv/ty//Tk9vfFy/80/4NP9X/5x8+u3ZCLw5cYvN2/f3v7sMtV+8+N7/069b33+6ea3v9KBRBDuaU7hx5/df59G"
    b"4P6n72/d+pK1uLn19bcE6Ns3+h/epbb/+snWjd+zPv+Dl9177avo6x9/QU+Ctul/+5fo40tvQi/9q0TZvU++237z8+1r71NH12/2"
    b"b3/KANzktTe/e2n77r9uvcswefVXW699B62pzrd/ZHA2b38QEdE4PX0W6LiUYxruab2iCSRt3vocoPJ36cuxRadrqSrLZf3rb9z7"
    b"8nOxLMdH6kr/xs1UXUU3T53E94Sz/Ekqm/0RtYl5zp+EMtbnhfNYlowIf5LK/udZfE/Gij9JZSfPUf/xKPInoYz1d/xxLEvGmD9J"
    b"ZU8SrGj04yep7IkZoiUWB/4klLH+TsxSO1FYkpf0lxlihiRMyYv8hUNnohELHH+SymafYpjfjKm5GVNzU8D03AUskwT1fLYoeZG/"
    b"cFGdpr5F+U5e0l+mCbok/+n5kPme28jlci17XmuExrLV7tlmhZkvGxzjrqbrmjOv0QfNAU/G7dqa3Q5sLQh9Xr8Aj45nmBEcXBYY"
    b"zcVedymvda1OBLDD7EdgW35zES1xoGv7qAL8+Hp1lwE2DqzbLsCZWpsiHo1e1w6almcbncKC7/Y8o2yaiFqHoaPrUfdxRZGaADqP"
    b"CaQSaKrv1bWuG2oOLHoqsUriHQZxO0S6NwcY791tXGztMx8DBNtWZ65laZ0KoOobTjcU0TLzWmCqmq9y6zg/PfFkfWdAea18UAA2"
    b"7/qaldfmEF/D0Pe+0HNDBKHvAoMEhmvv7v2H8H2Xvou9W54bSAXducCjFlpk7qR/UKPNIB7mEBfY6xH+anVY8726aSYMQyKDgm/D"
    b"Yq9pG4ihNHJBNDDw3elmRiVmz+Hac0fq40cYevlktCRgce2Lwb64ZjzigZkRxjUQN6nPtBjCkJKfMqjH1NgKIleK+nA6CwYsMmGg"
    b"nBftqr6yf2pS573hCpckDx5iuUOZg/eMyOl6VAO+AiGWHwYrTrho6MWiLjCcAeV+NU4iKIhlmhaAyfoPhQXrg+zo6bUh/5YGHPP4"
    b"udiBrT1XrCO/oxVnXovpUbQrhkWvuAJTBUeIXhBJZI7QjtOMqHM2YgVpqEJ/LcGtCz3Mt12LDxISVGKQ7NWm7YXaDP04bncIX7va"
    b"4apWGlrhCKw5SpNTsHwbH9f2Z6uOFcrzx3VtTDO6WlGsag6AMamCUZo/rYAxKbGGqp1MVYsF2/YabWvObhu2x9lFqrSqnCJxWW3P"
    b"7vW6MMWgNXLy0oZZWLBDQ0cYMLmTeUSCAx73/X97mzEJRwlFmkYr3RwLdTPmBNW1ui2SeEn31y4G47WLrUJ9Hz6cPH28Dr8XETPE"
    b"gK+uhMFnpOljgVYbC+qMJ1QRu5C4hsWxJfJtS5IoJjoKU4AIUskg2eBvkS9J5FIDNMhX/rx55109Hhrf7sBiynBCu8P7nXNC1HW1"
    b"etQffmMsQwUlTm6sWrA8z+62DLSxWLPGatUTzibtg6br24MA6H997woKLDKMAWLV62YuU3X77tvbH76np6Bby9ZcG+BzK9v/9sq9"
    b"X3+iy3Kq/edfNL3wvAvaHSHGfKCIW4OHEQ0MHXI03V6YcCOwbZzbAXSX2DlyAFA/gSDMO92W1W6jiQCN6DTbNlmKZhsWndVd5DTQ"
    b"knKiafktet0F4nXxfH386OEib4FmRUCAsHdaKAmit6JTYNO3A7fnN+0Jp6WT/Cvq4KcYUuiEbVsNiz4NhBL3xKvFELlEIorQEh9Z"
    b"H/CCZeiwANcqkglvut3Q6fbsxC5DlYLVahnQREBWVKpUYC2gbGJgtQD6tRUYKjqgEiNDr9UFRAfrXgE0H2iBMCdwumDfuuAvYB2M"
    b"eAWhuVPjtOk+DIYXRWFf4De5+7gv7T4qSaZJENsTBbl8UglGRiD2WZz2M77v+mqopUIpGYMQfCa1aDRBOYV2a8IKBX7yQoQyGP2k"
    b"EjonGPsudJbwhz2D1vDojTqvVcqH6tDn2E8mxjoTY63ZsacqY6crY+dRzZOSJhS5RzPauKqwhDkdqZJLUmUd5koFxVb2OJmpqTDB"
    b"Tn0ClQFfVDyDbhdcfy3tvuqo6akJanxVQ7fXDbFduiEJdkWrrZLaWcWpRYKHWjAR0tU8rndMsmWr9RQI0s0V7moq+mYaPt0xE7EK"
    b"k5o0/Yy/8JU/pb57ThM73HFJlO6SK3MlaxNNXwVDG/o9W2i+ISl8GOrYZ3P9kEwUzOG5tWjpiDHvKs1p9i02W3NrBJ3TnqhiaFAg"
    b"UEv2WpUviVYrmjGxGlusvIYvkh202wnImGWjAY2qq8EG9ghgSkgQ4scZV2dcL4sQ2XOqs8gEywsb6CZi6rILShgL5KV4LZlXOlRp"
    b"0LwCeA5Clj/xuQUf6Sn9mcsPrlugCr7VzVQV5sPg1IjcmVVeZSOZKYhjHbDerU38sH/iFiBAU24Wtp3uUqDBBMcdPjcErdHSQlf7"
    b"p3KpdPLxYqB5to82sGs3UWEVoJaNO5C0q+j12u1Ae/zUmWMnyWNs8d1FzcWtvLPT56ZPnZo5pQVuc8kGTw2n+YoPohsgFNyiay4B"
    b"LKDY9Vu4uxe4mgWAugtgk3GPE4CAfrCtjraA7WEyLiy218BlX0UA0L7bWnFa4WIhl7twfqZx9tyZH/8EZsgszLIcw6qqTR44qB0+"
    b"DG1yT81MP9GIig9O8dIYS9ohIRCNs2fO0SbJo4cm9+dyjdMnTmOU/pK+7LRst7g60bFC3w2WKILZWaJ4OvvU8aaoDH6EsklUu3oY"
    b"SAFa9vGFntMkG0PNXAEU7pdgIf3GpdB3QE/4yVp2FCBXJ+bby/gZf6SGEysd+oA/Anr2AsN5Qd/INWZ+PJvQi7RVtCzZeUZiRSQb"
    b"y6aWU2VyMARZUJHYkmdEV7LsyHPKKxI/0gCRA5Usb/KM+IrMkjyjvJJhSRoqsqIi8YcIthWluKEl07wBAnP2zBmUp+yut9GxVhsr"
    b"rr9k+0E1ljxaoTZAMKexVbzRXqDZC957Y/bMyZmnccPg0gZ/aZyfeQa9uFI9B4/nnp05B28YRYxeG1zOE2inYBYmAZzADgJDiBfB"
    b"BCPjxdAAyrACUIgwk4VnFKuUo1TRxnvhPLQBJWEkjldQAJMXhA27uwwVn7RAlcffWFcF7AgXKurglu/O2SwKtAh0ANs4zovQpOU0"
    b"QyMqZqU1/RxqILAaYLzm1kDVVEsTJT0b9/BpsU1MoCWZ2EV1MU+pD2CQq8ajeW2yZOa5Iqqibhnm9buwKpMcOJWHXaSAJwYQCrxL"
    b"tizEtYbdDSdIi/J1geDF8lHoVDIxxqjbVFRNqkdm3cf4V9gLGk23ZaOFnyyVhoMbgGLb7i6EixlfntzYcM1Dh31QU/wcE1cIvLYD"
    b"Hx/TTRDmKDwCor9i+4YMl8sGIZdnvcTfYTELa9nUYPiFZtsNbGPEeFYpL4S759o4XUSpyFOU+IHFb6wFqwOKrAgh3FGFrww4TR1Q"
    b"SZ8keZmB5eF3A0YXxfdgag3oWw64VCfO0GrLkJomLJ/rzQOaSITl+9aaMBgUSSBHpQDG3G/wgTXKZFIfSXUGcAr2aogrmKaZ5jnx"
    b"yIAqPEaRHsZkCMVxAd8J6CcnWBoVeYbzHQ42kixMA4xGd5G9cIZjQTI0g6Vk3lnFKRHHcOA9G1qAQgWrxYhuPNC4UHZWWSjQgEUF"
    b"hvvS4KQwchbcMKIAvNjbALYoBBw4TTEgrXEWnTxDnYrFOQ76OXSbbrsBDh+qfpR7rFwsF0DrUhUctra70OiAvFsLsHy22/N5bdzy"
    b"FwJBUjDVIanfchvorVFdcUsEXgsNyhQz2FQQWxyfmR3WgIyP0IIXM3SQBQ23217LRkepRsGzwM3kuuoo6SpSYEXQYD5TWvyZVSnC"
    b"eJbN2kS5Lg0WzntmzEmGsIcIaIGAZiQAW6XiIYhOANOpYdP0nSpNqfTkkDANZwpMSDaD0mgA1iJHRoxeyCPI4DPmsl5AB6j5LFqb"
    b"ZHpRaca+RLYlqdcUzUmaewREYaHzMSDuYQybSSkDTB8ZdjjJ6ElRg+GFNVhXgN/3Rzo95gdKk0PHnDa5gOXdFsZn/dBhTkme83oC"
    b"l9OyM8ZdFHDxyUNhtgvclHFzgv4X5JmQkCz6ObWfkvVRaH+1qol7sNHzZMa/sbIOCdHDRcQyM5+BTv5xjiI1cyxmEBOb9YPmBvcB"
    b"LrohcIpBHdSnuouE5bQUTdHHOjpSVQ20PNi+HXhuF8zfVPmgOaQeGxRDP8Y9LDYuee6CaONF5oFQfw8C5xRz8gBQSR/QLmkWGNkq"
    b"KbFkPOs4XYMkM2aemRtCO7gvyLWIpzSy4Neo2qTxn8VZlk8mYLy6JfEFhRT5mdIC3hwGerqJyo9xOIhZLAs/R3XQFN5htMhh5CNm"
    b"iBOZDd8odMfjhjtdyPQJLnT7tHIagHoAgYpYVVeGaRqqlYxr1I0QayFlAzWGrJoQCO1VoWFyPbvLDROnPupjVEs03FNT+GEGc8SA"
    b"aGxKEhZ5ZGr3bJiLlnXTvq+r9r1Y47ngyM3TTmA8NvtwCC5txHVWFh2MsLkB7ttjBYzMwYrOgHamdjiO3KXY2gtr0AbRpQgH7n13"
    b"wGcQffLI2BMWKBDYyT4tJQkyI6lKldUZLCPxogOpktcdU6VD6RVOLN4r80BqgaKO4vJDuV4kyOKSkTyOnp9iZYqNWIGxUTHhxe6B"
    b"fwXP9QxoAI6iHfTaoWFmZCoZlSxF/6gRGDgKEQPiD4l/R7Io+nfCOkxaIQ/0pkZdLatWzNJ0erCV8/daMGfEYuRldLQRwRewNG8b"
    b"FD6Pwm8LbXcODBsP3FERpidpYiRPWutHET8nILzlgJyYQYCJRpVisTz5CB0hKVcYb3l7fuSmYbVaII1BTVir4GSjIzO4yMcxMpLA"
    b"eF4TguT7MJcu5WCnZy5NBn85DohKp3cMQ4/Rw2QC6BQGjS09U/ErpvPPnFfsESs36nm/hZZld9xug0VCA5VTlgRJGYYGDBJIWRVb"
    b"E5MawBB7GbcollZw4Vq9pHtuu90A5xA+w0qgopUK+zcUyX/iP4YIE0WWh5YSqCSUCz0/yIgi2+T00ljcXO8fLW3KAY9lbLEXttyV"
    b"rsI5TImhaoYNt/PxqlPNQwqHMzYQBxqgLqTsISvAFaA0I8XEJfw+KG9pCMuSAD0GCUBzJgZjyV6jdKtV0nCGXHNcmzx4YGpq/4FH"
    b"DpZNba9WWp3n/8wU7PM1AFTnLk7KGqEV57VM7Yh2MBXdjaIPaIe64AAjP/y4gSnG++N0uaC4XBwLCmMBYY1cySMlecHDAkh8GUgO"
    b"dBxCYifuDPbD2U7WA2aOEzYaynhNwHYRohGUvvWayuIXlpTFDb5lPuBLwwrTeSX0Dbc1QRlkNizYVzS1qo0VudaiS8EjRc/4ZWDP"
    b"bWuNbfPI5aG7ZHcD9iVmIrKQW2AWX63q+mBeRlEfMKEXpk0FV6UKjQvHTAWL5TrPnByWDNTzcGVVICwZfg8eSfrBO+ATdLiUAfsf"
    b"aJ+dZscOF92WGKgCanqWOfKeVpbUIZtcI1CagImCKz2vZYHDeEm/ALpxYnoBnFywMD0LzyKw9edMlx1Nxr3HhRcdL4+0tKGRvmFm"
    b"U+4TYnG2MpGR9hxQTBPniR8TxIhPEH3z7Xnbt316S3l5KTQvTCdongLfoWct0O72i4sTx57Ov7j42AvVUuGQviE5Ywx6yh0H/5CV"
    b"k4fI66SXqIB+qlnEPmlrJs6ox91GDMLQb2LS+OkLYc6IHSk2PhOAo0yzjMz4gUf5/cO2f/hvZomAbUXUcfUGZSNt7WE9mwsPMlV8"
    b"Rf1NJ931AYEcqh7CZE4FLh9AyAcwIp5u35Mfo9H+sIgQvKx4ZsH6KWxgtqc4v+bc1lp6lsWTKjON2KShzA7PaztNC9EoIkzgASBc"
    b"pKMeeW28OJ7JWZBCXgoIjzUXMW04rF6YfRIGeOMfP416zZ2lH5nGhhuT5aqULNvqdbzAQM6ZSing2km5N4xDS2NgquYJ4SbY1uEj"
    b"zkFGFveHmaLo1gdBYKIE7pQL1HVX0LvAjFPKNpUWrYJXw/L/VzC0Jzk0h7XoGLeSnKRy4jiiL5v4NpVMvFp0igbOKgE1mFdCerHK"
    b"r5JWYBnpoNswIlWKCoFuY9in6fGFGXpikOJvqRAfd/1U2fIsRrvABSKFKsoNNB0QToo8SomBgzxL1SAqA0/D3c5BDB7m1AC9lK1o"
    b"hE5LEC5c15Pr3mDHPKAaLvHxJHlm2GmxgkS0Bo45NB+kE3+o56YFoK9scT8R3wOuXFNnDubdHgbI+ZGHWj0vHHuIyMY8R6Q1ulog"
    b"Pv+QgoX/qG5VyATGgmSj9+LFYjYrJ4KfPUEwODgRnSQg8NKnJYdC6nqvSSdH6FqCKH+IavNcZMrm1FOBUmBGlDNuIKA8ISfE/Mjf"
    b"F3OzqQ1LvIWVaJV1XK9V9idzg/z/4W0YMnKz6DxaE+boC0vCeNKShg8nQ9Jbod3KIKAAWiWzag4q9B+tQlUtEmvqhLH6YCsncisA"
    b"jrzBAdVQi8IvUnBEnK9K3YkVhSCZ5TnMmuMOArvEIx+ZPtIxbBD5KLJdBXZ9Rz5aUglDYgEUdqOLsiUttwSukvLLXAPCrgzR1SCS"
    b"60WsbnxZSCI7aIFjtiXeDFBJ6pXmH/tfnDFFYuzRRiOsshBUfGaCMVAb18qlUsncISSmgdsDo8iSrmk49Wg8sYA/bowAJbtUihYP"
    b"lYhdG2y4BE+GiGAH1+j2JRbNwCcWzkhO4FFNcWuQNnKxUKXKmdRFYRqJL/u0QxhjZm2zazUqFqbJitVeys4SVi0P1gQW/SUdV39e"
    b"uFgt4UzvOGGVwtioXtKOZnwqDH7ItONv1n0Tlad0qoxTTt3BjJlEJs0nR6fwFSNQ6KXjDjdho5xLeNghowfnxRNV/49NL4/AXTj2"
    b"OFpwkMoBQHpNz3eFVswVKiuifC7bq1OwmJ0bNjByl5617E6xo55fHQv2zvtVr7mXTT98Z1KFT17L8RvzVKqrpp6+F8xA066W9jYQ"
    b"LKiAvXRytXoASvBURxX3vRq4716xgmae3tDlwDclRNzxwQH3/Lx0s1gBj+PbBiBpKj/weURTgfsFsiXFhYTkTNJy40H0RVVWGgND"
    b"3nQmBxkvnPmjZcxArYJHeVhRygndOe4ddZb1XqOsMYULO+fb1lJmV9UhH3BAk+zJQifM08aeYsd1oKcTH6/lrHCks7niPzzvxrNF"
    b"2ZCRAlSovgbGrqP9/RYeBONaCTe7dzIXkq8H8wdWUdGUYnpTsUEa+XnD1dsOqk5KQkrwpwNi6ItE92tFvp5EJZ9DeMJwMPOUhwVV"
    b"JwQHgKaoyNaN3/bfvtt/67o+mJXE9opiHAa3YEZUakOqCVVNI7KwQ9rTOfhKzDd2LJ4yBNWNshkbbZ5AEaDqPFAaZYqQCpa2ccTz"
    b"erGhxk0unPNZY02aaZ6LLdexUqT+oVq6VPWUZbDygnEje5hX2ziFQeH31KEziAJTjChGaxLbNWZU9BQH17AexbiAGXQwFH7x+Cy+"
    b"NiKxqDEmYbnkE+YGykPUMlIKeuDZdqvnNXhAFiNhQqxLPoKoZMgzJ/M7WfKEI/wyPiVHwLL+N7JiYye3nqwgx2ZEc/ggWpVwUuxV"
    b"OC3owQnX9IwvzgMrKi9c9j0FU4Rt+CF3FgTPBG6ilTz49/iRp23HBjgaMNwa1k3lmj6rIpK8sRE3aGKih3Iwy3AW1trINNrND3E2"
    b"W3iRw/N2k85WRgc6F/FSDIrpTZUn83RQMtqeaLrukmOz054YcXd8u5WB/rzlR/ICq3al9uFKJ3tuSOUWkVOAg6A/Fl1nAZ5plS/k"
    b"mwUeiSqwm0OSPC/Ao8ARVmTf7uggJd3qKlekuaRuwge3ph+jrlkC99KgABgKyMAjFixp8KFEj/nlwbG1AeF9GqN7qdhx1PFfb/xG"
    b"uqZY2Kdwgmcx0fVJ1+9YwlZgFsic67YNhTuClU3hGEXH6vasNgE9tmg3lwbgxEKacSvcBOdbFhwJUKBhnCMwYiCcNtnTgfBof32k"
    b"QDhWTlL9MGfBJq/6ko5rF6Z38Sw/vXHHqcuOauM1bOCGNqMAqpA9RaQE8kY+nlznoJma9o01yjuOXxjYtSTniminQ6CMAYWwQ7ch"
    b"PKiLm/k3EPCEVsaD9mWzPjBknBCcTroloqOYRy2XDdHAJ1SHxGbMd+b81Le/utP/6DUswWQBstkK8nRSEGgbGQf1/pXf3P/pb3TO"
    b"Q7DzdWAM/7jASxcYUxcQZ3axaF0RTIpRo/suBMz6N272X7/9UDGzeKnFMLMQM7oPdChidO+BiNjX/2fzzt2HgxhJ5rDO59bErrfe"
    b"+Fn/9psP3PX9O+/d++JjoWv0OujL1o3L9757u3/lE9RU0ffocofhoT8O4d6XL/Wvvhy3ZTdBbKQZKgalMfmWDDgTxko098kPI0GG"
    b"Mv60oUjgyWeSeRjMPKqiTO4nfZKVH1OYggY0K2lXiPUQ7VxlPCUxFk9F7N4MvOSFheP5xb+ZWPwlFneo8Bsx2GUjzJWCZUmtcrBU"
    b"N4U0o+hyGFldhxRuWYj0dpSCJJ3oo9AVHqcBnUJHieMr1J7AsWJXpXkLbM0pHkwI2R1SIe1eCdu1ITtowB9kX5AV8tBEZqt3B5Y2"
    b"rVD8mmydiTYHPlRUW4w7DQQ8JGMArqLPr0pjGPMDYSSGcniZqo7cIwMMBdA13b5TF3YqYDJl+yRlJ3eJRQ9CI4EgIvGpLhm7bIf8"
    b"xh6xQywauUM0k8mtMtgrPtbTgywKdAqDObyqyMycPMSoAF0MIwlvkEivwWru0+gudTyxpBWL9GJm5B1T7uGRBSMlkHS8jJYhVIPB"
    b"GScwFdacvShmrMeSqBhgeqOrl3gRzlyKRcE7AsjqTH5gsRIdf5RVAKImTnnm7ckTnnwAup8D531VL+sPZ67j/eZMVHB/LnPwn8cf"
    b"sZY6PWMIa8oCW/Bwf8SDUkJ/rb4hbhvCYtJ1KSsYN5Frshe0ynY5JA0i48RPDMf3AymvMQCKiGaHXaqoWF86cRRvVXGFg9VdMyIA"
    b"8QE2QjCUpr8iRkjEKWBLE4fYAIYApJ0VUKu8dMLz/08c9cRh2yvyxHFa4jl3RTy9BVgYCBasas9r2+norkOHFmrwUx+8KYfjv8w2"
    b"4qCiDGA5MqfLokUTsFlW5XgoA/lChJnNBEYxQTYHOhrQakMMlbI2jD3LjsJpUKT+sL+BMxYUMWyg2AhCOMOzgjix1AXnFj/2g0UD"
    b"tEt8I9gyOjziLWBJAbv3Sx8Q3qEq/Kgac1Y/3frplfu//tPWtZ9v3rre/+by1tV3+3/5w+at17Y++vMwIJgd3sA/bkNe85tvbX98"
    b"e8fqGNjC2n/49da1b/tXb9777n1YAWxfe+Xv37x+77t3+h9+tHX93zZvXd689dvtOz/f+ujGnq7btYWgU3RHrD74vsjFMrtj2mD3"
    b"g14q5SdLpY2j5uHiYjm+IXTI6XDeBb/JWnV/DR+6rL7M4EL3Hh752+VXjxq15/52+bXDRv1SOX+wtGHCy1G8DdfgV1NfNDOoicgM"
    b"up4ahj2RVqeZZY0h4uP5rmf74Vp1l7tQoYuid10M9nFpkC7XzGJC15IKsDKtAJICvp7ZBs1ynCGuvOkwCRzDt+EDz/6wxvYXlzfv"
    b"vBYPfRl4ffSwl5aIciQS3igSwfveWSKw4g4S0QFtQ6Na3YW1fYcChrs0mZ3jAwZBfd9ShN9QBqYx2frmnXv//Pr99/7U/+LrWuXv"
    b"33xQP1wM8A8JLQh8mnoQNlnN0PWD4YyKPHuqOpASg35BYV5k6Q30yq+7RE9A37x1B/AHpPHOcQYsl9pXwzZ45mhqsqQcTfypVabK"
    b"j2LQQf/r5U95WJJMlMv2RAarWxZ9St+zCI94rduBUklx9X5K82L/+SGaNKs1BTXI0g+TBH+WjZgZIJRJ9i1lgt1WTQZPh163bvx+"
    b"+3fvb/3qlXtf3Pzb5dfZNdD3/vTS1u23/nb5Oqno90B1Q+HmrVfZTdJQyDQ2qPF7X/4C/mMaW2W+oMOExW2nKxBAbwZDNUMBfRyJ"
    b"ADAnW//71/2rL2/e/t39V15HM3PjWv/NL7d+9vn2By+xC87//s3V/scf9K+/Ckau//FXW7+4+vdvrg03P4OIUWNDA0no7Nmzh28x"
    b"UFJi7LUTQWZuB2LE1uXBrdPMJZ+G85NcGs7VhIHPu3OpaLDnuu2dbwjkTjR6xlN5mmMctLiIpQBtnOVJaxSFAHb43vK5GfWWDv0J"
    b"K1NKMVV5ip0R/URvpSXd95JLLXDgI/vrV4N7ZEc5aDUUQYmyNqM/TSJtWwGPa8jW6FA8k3PbcwIAFEg78pQuSpl5QiHby5EzSVuY"
    b"E1dNJcRldrladK6jARXxbxqSK28gOgVY0QYGZqZEZxekv7k26nE4JRLKPHJGfnTiFpGpirdeMeG1KB8qtXQAdEHO0FLizhviTlkS"
    b"6QWu7alzjqAFNmxlTkgN3RVk0KBtfBuCIhVq9N0+JXJEb5wNjRTmsaJpZhVjiiUgGfYqrMySNkii3e11bB/PxeDa2G4Z1AGFR4Rb"
    b"jPF6RFIimVQdpcDhVIFe5J1r/CsULGWwf+X69vt3BmUM9j++1b/yGq+jmrOAuiIUgETHfNHHAgONz2f/vvXRWyausKj7nTaZdFjC"
    b"wPqFqf89Y8E6/Le+nk3RpkmlSKlSqo6mjZcKZwYSh8T2aAi8oFbZXyrVFboI28Z/emEs4DhF/+nD6QGkpb//IekM26tRglOdPbJ0"
    b"i3pEW24ob8da9z98eTe/2IJxlrQ5oWvmmajR5TzghOzmNoh9zK6qCbpgeSINN1IufZzxLOQpD0+mj5waRa5zdIF2XX1URZ25J2wd"
    b"syueU9vAbWsBYyYYGPCehBfpksAokJGKzEN5gcI6hr5HRxe0lF7uYDusxW+526On7uYjGHQDiE57XeiEmAMDjn5g8zBi5Chi0hBl"
    b"AcBb5jzsxoYUywpkXNaFEAU/9kFxJUpW4a41vRNhsVMu/SWZnpBmxEwvg1DOQihnrOe8kzSYzDaYzDaIhIi12Z9tsz/Thqs51mIq"
    b"22Iq0yIK16y0HuI4CDs+zUW7ER8tSVRESnVR8t7g4yUowrS1EMP7nkdMpEySfPqWQnbyJE+/k/x3P/+dqg/Jb9tpvsuUcaznVeFA"
    b"CcEYYJz1ODzfMR3GDhRuwm6wOS+uVZjJWvWAbXZLs8Loz2DT36JWm/yh6iY5qKE87reTnXxoM//B+Yh2rlQXrA57jS2PirXJAm5p"
    b"4Km9H06H+g5NiTJTdcARJkstniiKkzHRXxvOD5sOypzepAPScZOKzF5aJ7HlXBAKDSIvnTa+1QIgVMaLU5aia1LSd7te4txk2Md3"
    b"XlUSQjLbCewm0AojTbH9gDerVLTk0kLGgviqFUULvO2uwv8AYiU6NWojSgMnKWmBZIjZX42opm/NoYOI8Z9ZUKhrajeysqbaktQJ"
    b"UjasncjchLfiBgMnd3gm9gN6Rg/qFfHsv1SDjGodQYON7NOre+YmPp+Y7eGKRe3MjazohTufYXzZFdLRoV3f6mQzA9k1TckOGoZE"
    b"1zIXAwn3WEmrtICcNvESjjh1PkmOH+G+quiSD/UVV8kVLQ/hlirVjSHJDTyDrjIa5Wqg/wscG3Gx"
)
_EMBED['wp'] = ('免扫云盘.py',
    b"eNrsvWtfW8e1MP6eT7EftY2lGHQBTGwakuM4bpvTXHxip+05mOonJGEUhES1JQNx+f8gDjbYYIjju3F8N44dLs7FxmDMi+ebNOwt"
    b"8apf4VmX2XvPvknCcdL2/Jtfa7Rnz14zs2bNus2aNb/4P5GSWoh0Z3KRdO6oMjBc7M3nWhp+oTS92qQk86lM7ki7Uir2NO3GkoZA"
    b"INBQXv+8fPVSZeyKNjsRHhhW/jZ6Tom9ppQfXuay8uTE359NlNe+0L/8TJv5tDw+r5SvL2iT8+Ynf3822dBQOf5Yu3qqcnNK6VDK"
    b"Z77Sxh5H9Ln7+Ee7cwX+F9G/ntcXpiKbq1Pa8kykcvmMfuHziLbxUL90I1I59UibfgI1V8oTjyOx5paINn0T/gd/vtUm1iL61Elt"
    b"+mJEm5nSL12PlCcela8+i1Tmx6Hjkcrj2/CnofzpU+6CNnFSn74F3YeS8txpbeJE+RFA+P6Jfuru359d1Wfnyt/d2lwZ1b++Cb+1"
    b"8ftbx+9D7b8/m6IxzlXmz+o3Tmor96BQm52GTxo+2qdU5m/rX85q44/K5+7Dx5tr6/ACyvWzC/q559rMg8r3y/rFG1uXoc50+fKa"
    b"NrUBH5evfrf1xXNA3+bKGeXjREEpX/lM6ekJhhSAUTn5HWAO2oXxKpurOAv8LX/1w+inDQ3/efCD95Xy6kblyZJ24rL+7XmAtQWV"
    b"1he3Tk5Bq/rUp5WNyziaazfFdHFlwNvMEoG/0nCsQVECfenhQLsSkGc70Igvcon+tPWGy4rDA1jWQg+JgQy+D0cGhiMOYuHaajpR"
    b"SPYmurP4TYyK/lLKJPsOUrlZ1pPJFtMFWzX4KnckbStKDxXhN3YZHvrzKeobtQPPpWQ8mc/3ZWyFfyklCn0e5UxNVnl3txpXM6mO"
    b"oaGhXyv4UMz3pXP4aHwBE7Gd6j0JFfsaiBkFiWQynXWXxIu9hXQihS/2tAXgxUjDSENl6Tv90hmcniYFhwm/AgFYO4xb/f5N7dkM"
    b"kBgMGUs/2seksbnyBdHqVR41voJhauOnHa8bCFmNXAnp7+n1yuIdLNspPozgg2I9DCRyUHESm9opQMJqo24wVKRHRTELtx5MVZbG"
    b"KksLm08nN1dWA/rEBfj+Ci6JiQsMYHNtDcn8+DosEiDIzY1r5fMEpkkxJxKaludP0S8tQQ8iDOCH0VkmuB9GP8eVw3VgODxaWCRI"
    b"6jNLmyvT2s2HRO04cnniAb45qwic3/0wOkaLbuXO5soDaKWyuKpdu0qDxIZw/a6fN5ubgtXLHeLewDrXxr/lgSANwLA318bliQvA"
    b"szFlEfgtz1GgvHB1a3QS+Agu/Q5cxNfv6nOTyD2+eK6fuYvj2+DRTEU7tkZncW0vnQck4puTJzbXT+jjt+A994BIDLrAbegrK9ri"
    b"LeYglVsPgR9tjV7XLz5G9jT3tTa3rD19rM18vrl2uzx7AuDFFO3ZqBJVYECMP5liFa6sn1/Gmk2x5t3Qpa21S0hKe9rMHuCcS6wP"
    b"aNLG6niaAMJAsgl4SQT4QDqSyg/msnlswsYoBUSJI06c2Fx9yK8FZ51ZAtxhPZReDZn+gXyhqKjDqvEzb/76WM3njN/FTH/a+N2b"
    b"UHuzmW7jsWC+4GGDkDQK/lJKl9JKQlXi9Kuhp5DvV0qFLHwdHkgU1LRiVswX041KKWf8KGTTORC44pNkPpcsFQrpXDHcUyqWCmnV"
    b"+PAQNXkgn8/uH0onS8V8oVEZTGSKjdAqLIr+gWy6mE41WH2FjqhFtaFYGG4nHkPwjeJwIpUYAC5rgv/doUMH9nKZVZsH0BIuFTPZ"
    b"cCENoIzqH+JDQ3oomR4oKvvpTyaf44YkUDDF7+dzaSqmT4yCBpgHQEyxN5wYGEjnUsEd4fCOkKOz3Qk1HVYHMikAJNo9SE9Gw+9Q"
    b"4f5CIV/gz5LZhKqKSlyC/6XSPUomlykG1XS2p1EByQEtdgQCIasK/jcA3zY4u6C2Gk2/lU4AHnpK2YP50oBvD2y1zNG+98Fb77y7"
    b"P/7RXigJBt7Lf5LJZhORXeGoEnw3kyuB4NibSxXymZQSi/1aea85Gn3tP1sO7lPeKmWyqciHv/+vWBjKdje3haPR5l8rg0dDSsDW"
    b"dyWwdwAo4I/p7t9nipFdLa+FW9qU4O9/d+i9dxuVbKYvrfw2nezLh5Q/wJzDTEVaoe19vTDEdOS118LRcMvutl3hWHPUBfe9//qv"
    b"twr5QTVdiLSFm5VDbx2MRFt3vRZrVd7Ld8MKVQ4mehKFjGgzEGo4sM9znH/M5GAtq8r7h5RYNBz9tQIFba2/VobaWkNKnZ2X+gZC"
    b"qSmZzZdSTalC5mg60hzeBSgyhhSLQhPh1t172sKxtqiyP5tOFgsw6tjucAtUbG3qbn1td+ueGNSzAbWNBYAlcrl0NjKQ7OuL54u9"
    b"6UIc1JRQw6E/VJvJj6TJhLn6pLcpmfu18ofm5pbde8WE/qE19to7H9rHY0dBSzjmiQEnzqEedOjtvR8e4i4F3k4UioCM2J5gCn61"
    b"Z/Ih4H1/eOft/R/E9//pEHZ6R7h/oHVHowJ/+47S36JKfzJqnv4W+o9204/E0QzXy3O9/oH0EfED/trpZEd4sJ9rtRwZ4K/VHq7c"
    b"yuU9Wf57NM/Q1WKhn5vn+j1YzwU03c2V+ptFL/NHjgKjQEvl5f0H0Fhis2DVF25rE6AdTVSW7unHx7dufr81egVkiT4zq81cQCvm"
    b"5bZ+YO/78Q/3H4TJ6aTxBwMf7Qs0wo9COoycHWY8WAj0FosD6pvtkQgR/OFwKXk4nMxF1EhntGlPoumTvU3/07Uz+Gb74TcHBlMd"
    b"hwd3ht4MhEKNAiJLfYTqDRTUusNh0rC2A7V8+bm2eq8G1O5EJlU6jK9tYOOHm6pABsnuDxa+GhwcPBwOvQm/oCY081f407a7Ff8A"
    b"J8M/e2LN+GfXnubQ4TDUAzh/TeZC2IfDg2bbnX8+HNjx+huH1a5Xbe1XNsa3rj6pMbKhUi6bzphDY7A2pH9V3njmD4QY2OFwbPce"
    b"Qjp0qBj5K5B8RO1NFNKH30S9oCMEcG1Qty5tgFFXJ3YS2cxwKUck81f4Dd0OSf21wS3Pr2mn7lfpbQJBQXdb9jAIABARELoaGhpQ"
    b"zPYn+tJxNa2ijAmWEh2m4BOyVgUiN3WQg6JeiF+Fe0HBAfEULg2kEsV08FjgI5A6TXuPgDYENlEpMcIVMz02FSOjKrl8kQStksil"
    b"hJ4hlVpS3pTtxn8FoZPQN8FivpjIdsQaQfEAZtvTE+9JJEHP6oiGmxsVtZgoltR4T74Aem9GLXZ0tjbvaVR2RaP4TzP+09IVskFP"
    b"mEqQ1N9gf2Ioju1m0moHtd+oDIBWBzocCJskqlFqx25RBnXVzCfpjpZmO2QVeHIpVwzy5MDcwKyJ1qpU9KnnrcXZtCKBq1Ihp6hi"
    b"puPpnAr6aRx0xKCaKabFBIOurZ88q5+5pX9/euv8nHYcjNMrW/cu6F/fBA6qTSxXlu6C/QSWhj45rfxu/963Fa4M7LZFVSqPx+EV"
    b"2zTaqRuV9XV97vrW1cfIntfmUJEXFIBNho+kYWTYg3i+T9bmuKv0mO8D9P8mkVVZCYXpU0qgDNL3nQH8N9BVhUBENSbUQBeRaLDU"
    b"SFZCvlTsiIV3AUaz2fwgzGkqU4AJVDsOFUrpkAcY6GigC7pTsr2jHuInttJu0Pb76pwioJwi6B4MgJsykNIlwwa04ZrI91mf/0Jh"
    b"xxZP1dbx9crGl2Alb66cgmkrnzinX1hQdilgXG2dvY4G7tPT2uwZfWkGppOnJ8J+MjC8QHBWnnxb2TiJVvYJsMDWywuTDXYMxFOA"
    b"vzgQZIYxgWgM4z9g/u1UWqJRQVxIrXGcXYF5spMsrMPyELyiAxc4LNhMLlEY7qB5FnSAy058TXRiAyD+WmDEXwXI45hgM4UwGWZg"
    b"5AGkHeQL3SEvhEIY8Q68CfHKHVDS0D68KIKJ0YD/vWwtBSxo4VkjNyN5OGRP45R+7W7l5APtzHVRj2dH+F5fbm/Y1vpo39soWxjn"
    b"oPrvPfAOqqEGX2JTHnQVlG8xFngkjHghf3Bg//vOT/JgD+JHrNjzp1z74O/2frgfNCWSIfVoRkFZiQmZukYQlQ2U9g0NhnkYj6OB"
    b"GI8LE5E9OnYTEd+EhYOoQ9Swv4yr5PqLJxPJXqxzbMTxvh9eZHLpOMp10zbkZWghFlbk1zCrUonVS0GmaO/3g+BEqC62pxwLfJju"
    b"SRfSBXQkGliVkdmoBPYZ7kt5VED8AXxpE7tkzo00uPuQyFXpgRsEwN2bRPbVtF8sK+weGOrADIrD2GyNXst9GMirxTh6bcR80eLu"
    b"zqeGnYzBWPDNUamXvakC6iE+vdzHq7rpEPu2AwkwzDLJBLLdCDb5ayXZix6dYgfxhIA1ycAHROt2/oztGUqNqBCSUKYOyEoRDo2Z"
    b"FTbWYR8UQnJxMTssmWsFuIfO6aFqzKMMjJLCyZ5rgVJYKPFMqpHkP+mhtsUAHQT4PYFjRD+87kdYbeV/BxJH0hGC92Y8Xuw4lgEl"
    b"ROb2rypge0dDI1bncKQ0K9wyoN7oQsDoA5aJn0ysFu5xOMTxcZ1Z5CERBr9yrKCQhTyYngS6JOGzMHoc1SDCtN7z4kYLGmuy7oG/"
    b"AiEhNbiIqyE9B0IyZXC5Q7twcY1OHjPKRi52zh222Gi8sxYENC3g1DV90B+uQKqQqxcuJZkUP9/OmrXjjRaWqLpMVs4ehZxDcw4K"
    b"tez4UeAQeVUMisHRnErjQg9Jf6bYIS9x0BQrG+e0q18qncd29GRSOxp3oDs5jptY8BuVavxD8OA1dxFKuJP4iktGrMFRI29EFVJd"
    b"n4MmyyXK5sqDyvyJrVuf417a2BxuvNGWhza3ql9e0san9fPf6Tc+3xqb1s6cADFsKLH4X7+BKEO0hXmPLGiOlOncRkmow/V7TlGn"
    b"1VsD26gHwm9opz98pJAvDQRjoUbzt2RWDCShjry6jC+pA1U0ZNuEy4RoTniyXlvDPQwxXK/F464MvBB9KF0OqTuYyPaZnWFIsDqj"
    b"QDekAqagJ70dUYOK6F8XbUJNabURRPs6M+AOgBGAFCUD9yJQGBi9U95QYs2I4yBTE1qwWUAe8nXljQ7+MuQ1cmvmgNXCuGNmwWAv"
    b"+ghR7bd/x0w7WItrp9LFRCb75kCh46N9wvX7Sk+hYyDpcA3zfz2BVxgHHcf478grjIuOY7TFEeSn0MgrBmqgovg14geRrOyO6Ctx"
    b"7BDUh39HXomTKbwLStV8odhB6xk3oNsTarLRXN34FLBbXwVZvpq2gCFTveWCZOJFHdCqSVhJkBTCJIHsH4MV1K/WlCHI+bhIImZp"
    b"ORCUdhfu7DajYe4CUQGT9/kEAGaKoh+ZgnNHpI51ZHwNsxmgVRWSKR+Mupig/pALcjortY7zB0NG8jeKQOdKH8kXhqEYBhAEQM0+"
    b"/YMGjX2kY9STdme/AqFGzy9tWx0mDdm+N8oAij73QPt8XZudrgsckqsEiR4blWhdn9oFkwzF8abesbmVKtUAzT9GQl7EUYUpeU+F"
    b"gzcZYOBjosCQ8rqyK1oP6RJX24lszW0hcTDN1hfPlRhuaNtDaHiLGQStlwVlbCeTf8S0YCw23iP+YezaFQpt+RFGHch71mbrvOWs"
    b"n96wtYBOrDuPKt/dZV2k/NXq5so3gR8jTUMOcVxdnprQAh5qNoxShdnvhL9djQo9mtTWaaIAXzlpp8FNr3ZaQuoaSKdTpQHDF0zx"
    b"NiM1zAfbhn9V+bNdbZ9mehu6fqKAMsOLR7t1E6jrqZgEXHYX1OyMdgmIEpnwIhYza5LqQDYxTB0f7s+X1G3QqUGgfwEzS8RbTJzQ"
    b"zy0BsVZur/A6AcaMIRfane+QRse/3Tq3iLQtTHAcu9Q/qLzj8OEdsLb2vf2+AoRcWT6+Nfmdfu14ZfGOtnjcodSmssbUuFebT/+d"
    b"OE1lPVEKtiFa3kBMoK6RO7WdPRY8z4Y7wzHtIw11gEllPcjaBPtjHRopxGHg8OHAiOTFUIvA9PrjiWzmaFpMb0ryUbbZZ5W95ArO"
    b"AE8hBinN3ivPXcfAqe/HtJOr2sLFyqlPYZo+xGg5JdoUxQk23OsYnSSiEGfBPnmiP/qUpn+SA7b4v8pnVzD8Z/lR5cnn2tx9rl9Z"
    b"fK7dOck+4crG5a2TU6aXOFK59VA/fRY9jwz6Mvoi9RtPys++0E58oy+sKX87cVbRJu6gV3hmCWrJpFJ9ui23vffmjVOtS0la3YvM"
    b"WE0pKpGGx9zijCPiKShwuJhWO2AGAiM1wDIV0J5BFc+OuVFQCIuNKDLTUC9qxh2o5mibU0tNZvNq2qF+GtZM3/YMMp6Il+/OloPl"
    b"JI+2FdtKXmuoiGGxH+1TtEXgVfe1pafl+WXgcEBp2t2L+tyqNvEYJTGFgIGOVtk4qc9dZ8Jj6fzovPZsFFYIG+rSGxEwNrOkzVyg"
    b"YuJwxqKBcqB0aP9vl8YV5pLlB2PlG7BqrnAA3ebK6cr6Oqg072XeUojTPuZoW1g8CkiwUnKgkFfM0Nut0StbY1/QSpoCsIoCSxF9"
    b"9ysPFHu0W/nhUvnTp/r0LX1iFuEMJAEz/RT8ERlMd+N3FJc3iUoJrNCbUwbE5uhv30L2r92Z1y+c3Fx7XB6fh/UIgzc1JG3xEuAc"
    b"9wmePEJB8Z8Hla2xk+jRaG6JxnYrm0+v4yCAvzx7GuARMihALIANCJ4h0EJzSHgDaQDg4LsfRmc3gVUsXRNu8h9GP0fFbG5aO3UT"
    b"Rga4YewD2yrfP62QDADks+GJPww0AKvZunyivLYAvdBmPqcBxuNqKpNSIvBjoHRE5b1CfXJ0c+0uMycgEYAqdkVWHmgrK1tfrSli"
    b"sxlI6ZvK90/0a3dNnoUOnVOnRFcp4Pr7J+W1yyZD47EqCgwBaHDr09uV50+3rt0whGUH43UnsgCY6ZOEChaPpP8heqBj4iMpVvQO"
    b"FDHxIm+cnYJ2fqpdmv/CwI6qGzXkaW8aSHIMiPduTc39F1cQSc0NGGMP0lryMG8mwfPqQVICKTM1yUtOrLLpm7zqEGUI5e134wc+"
    b"xBGhnvhy93WEDusfuuCsWSOSgbdUQjU3j15ka8i5I9NLur7H1grMlTnXfps+svvawpJjc6PT2EzqMtQ+Bw6FEOm1ZoUriC47e4yW"
    b"1voX2uQ0sxBY0LaQblxd+ulJ1Hg2xrdurmkr94AE/jZ6Dv6njT/TFp8q3J//BDUY5UYqk0Qn7Z3y/LS2fksfHZMVEFAEi6rdaZhE"
    b"MQvqRKJY5L6FzU3oAPdCBXzh9lLIXzdBz4aayYGsziXTwWRfI3XDw33BHQA7tzPwK7XjV2pA+ZUShOpHQ+S8wV8o5ZN9YbKfgyG7"
    b"Qwg3nN1A8cskf+ZtpVOrhstEajgZRlcHrJPw0US2lA5tO0ikFrXYGpZquRyugV8rgfDH+QyYDPhJ6H/15p+Nd/z8G4B2FkOS2VSn"
    b"WDiDtNUmLpavLuJxBw/u86+/fehcwNv0MMjOhXocDHWp3cdGGmUvwr83IP+1NiDFMZSJi2ia02JiWcZGCKywH7s1+e+dxH/vJP6L"
    b"7CSSJv+vvYvoolcrylCS3tW3F6vtK9a1t1hrf7H6qvDeafn3nuS/9yT/vSf50vYk3TuSrAj47EgCCRf6zSMTXqLAoVUQbLaNK/fG"
    b"DHfYTuEOE2eVDW+WPjmNh3BtzkU+/Mz/6d/cBAWlsnGSdXv94mNtfAJKRN6DU6dEQ08+Lx+nY8Wz97SJy+bukGJubDr2gJA6VeKN"
    b"RYlD/bymtdwHsJ/70sMuNd3bfDY+PMbmsGxOj7ygQRzg2QkgFAJfVQ67VaMa6kdnl0v7iG3LdndvkGdyPfntbI7bt8GZ9jc3bupj"
    b"uO94jHbZGgW/4VQSI3jSGxUCpbyG7nnhRJedfA6i+gfslhuIl5aoY3G+zI11NwPc7o45vyZf6Ihr0/yf08Z9qZvuErgMjo233N0b"
    b"wLzpa6oZPpvxXpEOQoDmikGbEKUvvORooJrwDoRGGl5ObErVKJRtrjPZ3rbzA5+u8MhefiSDHK5g21BCSWTbdzLLr+Jeyso93jNQ"
    b"WmPN/6zBCXJcQq+/Q3L7ZyZsjv0Ru+yVPK6G9902PKe/2O7cT/bVGUkhjbn3nzDg4UUjEF50mhr8Qgd8N2O84gh+opl0S4W67Vw5"
    b"3qK3cRuRDEIyoJNdSp0h//cLpXxmSbt1HFazfm5JnxoT0BVt5lP9/DLoqVujo6B56pcXt0avKL/dfwhZwsyD8tzp8qnH+uhY+caY"
    b"sTO43XG8vCAMb1R6RmbUNtxtKuU/YTCHnDYIlqeZOcidbyigTZ+vbHypn7nLaYcCGDWwcLsyf9uI96DAgsUvYRlvPr+mTy8CmOZo"
    b"c1tTLNYUi+Ku+uwU7pzPTvG54B9GxziQQv/mcnnxEXKGmdsiqRnu3DcpGDMyPo9HkenwvPLBwYO4mQqfc2SDsjscfe+tiIqQps9s"
    b"rqzygVhlj1lcGX9eWVwyi1ux2ADOYSwcSmIMTR87qy1eUaLhGEGAEfxtcmJ3NPr77gEjZmH6lvLRXiWi4I9eUL/w57mnijqA2y3j"
    b"0wpzNTqgu85RVbYGlVikNbI7EmsT6ZeUjjeoOfga87nQn9faMLFVuHWPIjpRXt3QR+e1mRvaqRscbaAofzt5FnSDLyqLq1Z6KAri"
    b"MAfzw+jnPFUYxsGKw7UvQcZqn18qL1won78rTmzfucL1Oa0c6BtgWaK5+QsOLtu4rJ2dCnAQRXl+GuBh9ggMVnmyWHlyDUX33H2e"
    b"UoBWGZ3CKBo887p2mQNLKutfw8IG6sJ5EsnHHsBb7cz18uRJKyhF//IxZiFcerq1PmsE7DJ9chAKjBNLN59e1+cmlTdT+Q4QSq+g"
    b"G7CD/P2v4HHlDuLIr4TD4Vc431PHr1KvJHtLuT5yIcIDCLyOX6lGm0a8SGVxY+vioiJO3MeaMb0OzEv765gq6I2IGnldzaTeQPlE"
    b"SwQDHt5X9Gs3y6e/Lj88LRDIy+j0pKDrxe9hxPrUpLY6o134VI5OMeJ+BJtkmokoxkYmPcOs7R/KHwA1LF1ARQoUJEW8kCJ5MA3b"
    b"+nlsbeEuhy0D3QGPBU5rKmIwmaDjhyn5VwdI25kl/fx3m+tfYHDUxQWG9fLDV97NJxPZgyQADhTyQ4KpxtEJYDtG+x9UvT9d7M2n"
    b"GqzMT4arIKva3eZQEGYgGdWRKYKTSRmvO/B30OXKNyv4xJs4g0ziauGonBHLekEJpjqUqKPY8My6DhKr6b94VM/mSTUwk5OFAW99"
    b"zhAVkbGtQ2lrlZIAELkJxkVZ3AQbWJrhwvLqPeQtyESIXcDH/AKY2i5mhrK4pZa6RX/adu1qaTNbMvnj0ox27SKufVLiuNWt8xv8"
    b"dnPl1NbNVaB2QdCsvlECUbfnzYgr83SviTQVoLQddceaGKEKNDOeKUOk6bblaHC7pUTKOFj1YW6M0sH1ql61VMBMuihVc4h2UDvS"
    b"hqrS4CBKXBDx3yVyqSyMB+CH30qoaUww8iEHJ4lXXrEmhXwxn8xn40c5CRi6OvDDSCwcCzS49xlwCzR/JN4PqlLiiKGxv5oI+cWU"
    b"GH4kJ5BUPo6JPpzIdzm4oB4ocsGQLxR8WwUIYQ0MLEIAV/RE3kGmBUB6+JCxVt7LDL2Ta8T5CiNKuIpHO6lEuj+fE3kPVa/MHeTK"
    b"EBlBSmo6nkilCoBBo6rX/juxBaNbmPtIiAx2zZuzHfL4VnAOE5CgPaPVzph9s8biDTzyYDFRABW4w/E9prlJA5gaTvy+QfgaY60H"
    b"8tkscD5A/9EE2oCgf4w0ClxxOhTUmAtF73BkGwpr+Oj8+KhbwTXoBrMIcpYaz1wFAZec/lUKY6Es9FqgCukjGbUo2IgIPLKHHJFm"
    b"AKZAId0D6O+lUrtZK96gpjWztDU6yccplGBIaXpDCebSgxxegD+McCEQukLZkXz/ZrwqxuRjvLOIjWOXB2oFpo8ftIhrF1mio+F0"
    b"7Ya2eBx0Tg5J1i8si8DLtQXt83UP21jEDtDuOSHFzlJDtU6/DGaKvZKE8pxQkGc75Y1nThmDYirwq+juIQpOC1p1X1Wa23a1trbs"
    b"eq0tFlJeUaJDvxH/ea0REqOdKke1GL4/wrLwU6C7FjcRgvY0MNvYT8sVg/hTOAEVY5bhlfg14rX9JHUvpLyh7GlrN8XkzANOg6vP"
    b"jVY2MNcsZlS99A0ISJzCi99VNmYrN6e0E+PawiX98X3PEMA+NE1x31ZuyNgH6Wxv3d1VbWuVaw/kBzAc0b4nYzgIMylJ86HsWbS7"
    b"LpaHLdoA6ApkOtgO+ugaDIJS4Z5h4d6umF4OOrdkU10Vyl99wUGWdterJwFmip38ustfZqNDh+YdKxuk4Eji1dspvDFIPJI/pvpR"
    b"FARI6Z5qe0iCuxuVWLPDt97PMdYihqcQiAQPp3aGDquv/hJkQsGMLyYk2PBleF9DTnrr99hoN1EErSEJW4E99s+TRXJ6eLZKkZKu"
    b"1pJF7+aSlDGcXFDFn8lVso2NOpN0XI59YV+g2yeTdBgYcfKBxguI/mBvqgBTi0tB1v5R9jUq6RwyNJAOnGkODPkY4oofKHVU1ObD"
    b"A1jtVamCqRFI49VQE/0LxAEf1TP3KnSndiiXrCcrHbgzRvvuaW++kRNklA55sxXEAraZGApGBZIABznv2owsE1EekRqqTzeMdogp"
    b"M0eu0gJ3GEeY5jnwnRyCa5sgfkkYgf+/Ibpr75XfOLBBePU6g/X6hl64YxQNUvKwhASHpeh4T2OoPzHcDZTKIsmHTbM2EBHqBagN"
    b"+vkJTAy+fBw9FeJbcQoUDyhdwKNYYPlbLgsw61Y3yvdPm7nJ9FOnts6NoTfOaIeP5ohqE08ACOb5u/idNv54c/0yl5cXJkFRgbfa"
    b"4hTnl8McrBeWyQ0xtTW2gT6yPW2KBWh2CgMYrn6pr84yUA9txljchoQO1eH4F4YsfKqmi4DIRCmLiQcLWA5Lzmlwh+yqj1vpQdKR"
    b"gpmbzE4ZU5NOxRNF0v6BQGK72lknmLjCoyKn2gSmz594iFnoBRZBK2R/m4fbm0fVnc9nzW1LFE8hZ3aKTkcXHEn6arNsWScmlHWa"
    b"mO4KEi8N4qbYMe/QHvjae02b8hTTJxayvnVMIW5Ido/Efj7IcRlyL+6Sd1gg8Z50MdkbJ3+IEUgMthkuvUZpQTuWIeaunzUdIj+M"
    b"fq5PTQpvCCwyPPt47aLpqBH5+y8tmR4bw12DS8UAwucZUdGfuUBf287+8nkafWxZu7sOFfS1m8pgIldUjF22K+XrC5WltYh+YQEP"
    b"7tGK1E5cRm/7mTU0Qxa/0mbPIHSwNjir5LnLm+vT+vR17dqMHHWEN73AhzMT+NXjcTxW+MW0tnrOVP3eTeeOFHvR5fnopn79C6Uv"
    b"nR5oon1D5HF09PO0ON1HH/LxH/Qf37muLT/aOjkNKJLHhv7N1mhLpDUWhf8343UYHraUYUhdoSCoJ6ZppJ2YhrWFDu6Jh8TLLleW"
    b"lrZufq+tf4GbUdOLJhpkhqP2CvFixclleopGpICh6R94/7dgwz2o3B6nzckrzMMR/9+PCd/qzLfl+TUExzNhcRecnQ6SFk1C6u2U"
    b"JAyaAIkiaPEDFG3J+klLqI7dvnr0Yj/d+FepJjagg0aP1F5WffBXyGdHTt2+2hwDHaIlGvLkI/YNOmL78iadN4/xREV1VbR+VuHL"
    b"MlyuSLuMzhRD/sCMxK/yvql+ekObWDZJF5f/yWmSDJeZZ1Tjgd0Bd7hxdwn41ZE8B8Q3Sk5n12mzAp5RK8RFWtQg+X19ei+EcbL2"
    b"2DwrQJ+M4Nqk94xgh3d2kJXtUwO6gJVAa8N15N8RdxhoVWLxJ5T6iMSTQOrpqzWFfG4OcARGPtbv+jFiTaIMS6CpuUxPj4/+iOon"
    b"7akCP1N2Aa9lrqVdHNfP3MKbeuaua4tfojy78YzuLhL3aWHGiIVLlY2rFBfuZN7icD8B1ie/whP9s9OcD4AzS2xu3KSj7bRpzEfq"
    b"m/coW1dPmEdvhHq4cEmbuy/rooqCNyH87cTZ9w60gsjB6xEi8E8Llvz+D7RPB5LzlJ1T74TKinZ2yln6+z+Is6Zbl76B15XlWe6z"
    b"eemQqQEb32D3J+/qZyblJBog61l4MvIq87e15TGoD3V2xUQ+ZvMoER3Wf16+swqqolKePyvjbnN1HiQTm/okfrroljFLxrB0kTZh"
    b"JnFUkq2Om8Y0ZYps8rvDaAJMFelUgGP7q0a4kqZp1O9yutF7eYequ1rsp6jDPJMVLJZwqFRhTvZYjCRtd93xn/aYXQthjQ7PhXBD"
    b"YufJRUs6pnXqgPRqwwlTzW3gggBfOqL65u6bS0mbnFZadxuL6cS4tngFyINnRlt8CjRTXnhOJzcnLNJ6dmXr5mMgLSXf0wOmixJ1"
    b"uIZFjswgjbRRoTFiUit6hqGakECF1FbvAQWj93hyGrNJnEG7j9vcfHYJNCa77mMBZJ+HnVhwwA6bCKphabgnA1y9O3B4KJY4PNS6"
    b"6/BQqufwUAJvgwAorbtDsrDb/9Z771LaDlh3NmgfO6D1QEc8INgijnBFd+eHlPKjNe1LzEdPKBcYx+xI+BJ9Qk4LC8bzMfLmVnIF"
    b"oFwL7lZeJ90vjLcIxUkzoknu/BhUtdb2jzH6tztzBAjlddyJ9ZCSOIKmWL35aH6BU6XgKKHfRj8VyisxwYlCXDH02OMo9Tj4MViZ"
    b"rUiyGewOddGjR445zcAQKFgiMtTUnygW8mpfItDgOkzDmPGBpojWXG+NRkQLdE0gan4Bg3gAkTsRkfBvWxe6proDfykG2FEjPgI+"
    b"7tEf+ri9RXzzm3f/EGiv1fpQU0/2qAcoVC4QHJ0/aXntNUImwY8S+OhQq1QW273bo7TltTaztGZH+geaizWH9M7bLQGcSy5t7iLV"
    b"F9dTD6yjnm5YBeZDi/zQ7HXSyuxAopTKYAfSR1weFarjCJ0QnzkDN8Lx9FAx3o++BGR2LueWRGFVWacNil37MHWD8TltFa/BxGv1"
    b"5u4r/YkjmaQCWgguipOr+jXcC6PL9WyCjEPi8+JyMnUgm8Gg9mDQOkDLhcHAm4EQZnPL5gdxEywk77Sa0bGoS2AYp0WQsGhQ27AK"
    b"pcWD75DS2u2E5xFTHi6qMtjmIsNtKe12Ji04mkuhppxN0+1NFKLtAS5xNGPrkUq/GGhe6pC1DkdI2AFqGuXRhVxOD5bJhqbo7+6w"
    b"4kLIt6Evfo8uLorkdU+SyvvpVbKxeJygAROzWCipxTheeNvh8PBtQzPwukTGOp5ud/V4OHks8zyTS2Sz9QTfUt9/xE6ItFNR6h+Q"
    b"JmMQDyP4zwlmRerkl/CuS8EbcydmywuTqA0sz5AHaeqPGLrm9lQFKuuLlfWvA9rsZ5WTD+xeJ0v/0E5cLj9cwri2axe11ZnK8y9Q"
    b"WcUAIwIrvFast4MudBqVF74/U1u5py2uK3+bnICq//ei4e1ymQ2UtIvcKtOV4+tASgH07UBHFqfKX3+txBSgNO0EGBAX8LEZHwNo"
    b"M396G5NmgWI9NyluzeW+zN3Xnn6jf7dmV+Z5sCCLoDqG6J24jAfvjq8DBtktDnoa3io2c8PIPSUsFSuQioZihVLBQGxHn2j/wN/X"
    b"80exrxJrVPrB9qOtDynaCzgXKBm4z7hbcpi8JT5qaX6tbXejYn7EgVv4DVnw1gc5ekNnhblDOwFGkwKKdiSivGWTC6ImqBPRqoYA"
    b"mPkpW8waGBmpTNG+mvHdsCMODuQCpUkK5Pgm4CifnhqAn7S0Rxps9z8O5gt9wKcHQ2624BVK4rsOq7OdOrlNfWt3W33LpIag7qCr"
    b"3O8Ev22HAifB3wHCIDh5QoKuQ0I0d/G5aGj2dXO2jZI3OoyqNDldQCd/bK8aTIE9CON1psFouCXkW5XSmMh9QJ2VGxR9qN6Mty+H"
    b"kG1suEFfEeKrEj3bpg3XDKwwWIjAOM0F4FlXHJCrKhiA7YbY9weTLV9lRpqslz+uzlmjNdMJQ+kSh+oaquIe2s30DMdBIvm4OBEp"
    b"OzuUP9rP8nvJsKruMY+h+o/BV/Bt051mc4kPWs5wnMg/NhqkE3K6xn1i5ZiVNCoU+xYcbAzViHRz4aLamqwxs/xp0L667AvQ/k74"
    b"vokaqi0Nw3K1La/qrudaC9Zrsdo7V8+y9V+yzPJsEKstQ0IBxTPBh74RClLvOpjmPWIP6ls1xtEyaN57eN5DI6UsPFgAw4MycoR8"
    b"avRkS2pv8IUytHku2yqUZ59Gn5hXN0LcAQrGKbzPyrMnvLMYWrG7jUqvK5LZtZTQSkNXD9eUjDbTPlOLhcxAMBBxxCgZif/kLyLu"
    b"OCY08TkBnfJ/OhRKr0OPaOEb20oBTFoQGCjku9NeJrTRNxVERhwzr+VzwM9ao62h6lXFqb6AfU9UJDTx/dT6UvUgSY9MGP35FMWt"
    b"pggZMDQ3UfjFbpqnrOWAQbq1L5MKeeeI+ZdDD0ZP0W1tHcYUmzGaoLdvjV7RR+fBwNFvj/IBRLBRlOZdbW+hDUHXALGvfSef9dk6"
    b"vg6fUDzv/ObqCb4jEU2CswteYRsipYCvj7t5165QnQhtjkbpnkKESKrFrmjzNjFMkX6NdvdCPllMF5t4gzbwojMGnwdxoWHnQqEX"
    b"nTwxOm9Wa4CQmSs1Vw8NSA5/3I81T6iS7513sUBM2DaCtLGZ8vwaujAMf5S0S2WfaMO041akKFpsqsk/gMAVUURw3AaXP01snwR+"
    b"okVmi48UgfdyTKWAa4s/FdGuRrClDV6WulnFXObeqgwfd5owMKpaM46YYJ8l1kbeaRMurTNYeFU+9lljZrop2nSiCReh94bj02u3"
    b"qY52xDl1GhWJLdqaCGyjh85VCw8hFy2aOGjfHn0xto1uKRRLEpHDSYhIjDn37rU/9QnKQh8YMlAbT/D20VXXqbxjZ3yWWvRnXmr1"
    b"+gZf+jnwWHOLsrlaJaW/uKSWzuX2p8GkinRH+sMfJ44mFOCZ+p3pnyoL+oFEDjrXXl8u8x95x3xQ3AYfsvnEfZJ0m/sFBXdqCOhE"
    b"mJvHXiI95AuZI5lctTpuD/9ANlEE47cfv8ILduNmAebtwIwWCZHR4u29Hx7inBYg55vESUH8rMV+AyvyZ2dWVGlILzkfKSVSsXwh"
    b"felhW/C6DATe4bJQUXUNBsK9xf6sUy3nz+HfzvamXbZMp/bsTwPOgPvON1/pgmmGin89iOM4MJgKcTb7gIQGj5ENOIbFTQ14jEAM"
    b"GDpHOXLqykZrd9tvjZ7V1s9SHBhGvmgnxs2Ms/KdmNl03C/5bLqYOIJPLdAL+CtnynGknTW6aZfb1iS7phc++DHJV432SP2Vk67W"
    b"n2fVAgF9BZqP21Os+mVWfcmJU72Wbg4YYWIgI9Kognh/U6Ryi0ZfOSClMEX/REdTzC/tab4APOat4Q5zYrnkbbqdHhZzR0JNvsJj"
    b"/w1UeQdTqRqY8M2lSn36fXq44xjgb+QVg/opXevIi9+3aEuIumubFy16yt+fLDtq9fSo7+R68u9SitSfJUcqmF98IIHPYhlZSRuV"
    b"Jg9fNCUxtGrjpL9vJiDzsqMIunB34MfGJrfFV//wztv7P4jv/9Oh+rKfEq+RkqAx3b1QElQaDDJYK/Hp9vOeHtxG3lNkhtKn+/Gx"
    b"3o4TB5XbbYEl9JvsNiDYUtNZgN4WxR8ZOddGauSy5WN6OKsx2jRxFUdNF7BXG7WT8Fps1TXJUVf+3VDVZKzA714gG6t3qAjlnksR"
    b"6wvKuJQvI6Dcx/J9dyLQo5CGr5PpYCDe3Ar/c6wX/Kxk1XmFMtJTKumO2CuDHc2tr/TiP8UCMLo4YKeD2XxTsbfU351LZLJSvhkH"
    b"6CrZ1UrVr6n7qRRIP10SaKaQ53TGdWuRIz+B0VF+eLn86dMtsDPWMVlUbDeW0NEXzNckGRxGlZdtYRx859D+g6i2EOqOBYjdAY+6"
    b"r409BuyYaSCtokBR3DEymO4m6WqgPYDJhzBXqDk9MDXhtra25j2x8NDwJ5RTULyBUtubBidpSBPcX8qXwgS70eNFQs0kAl3GbXXG"
    b"AMpnvnIOwCyyBpA/csS/89gC1gjn0kVby1g2NJTP58PJHucLpETzndEro1N4fOjOFVunzKJtYLV4NDw8nFKH1TDua0gdsF4kk47y"
    b"5ljrrmbGtbNX+tfz+sKUfa6Nom30ajCfB1QNwT/pUjhfOGLHjPGup5RzvWhtie5qjnr2bXN1SluesfXNLNpO32Aqm4cyiTxOjwNp"
    b"9vJqdJguYNVPet0wTPieL9NDgwM4I87BVS6f0S98bhucWeQxOMe4AHLL7vBrbeHYntfCsdea22Nte9r2uGlu46F+6Yad5oyiF2mk"
    b"GcjIPZJTj7TpJ/aRGEW1GzEw2PvxJ72gOScyhEH34lkpTzx2LB5RZLbR3a36gu/r+WSY1nKXSSdkHsfV4nCWvsY9NZOISsk4qJMq"
    b"SacYvt2DkJvxF+a3AYEAv0i2tgr50EjO9XPfa+uPItrk/NbVE5Hy2rPK5GpEO3Vff/ZQABZQO48FSLBwTYRzlGEDHPGqfH0B3pqv"
    b"mqVXDNF81eK+rtOAQT0wK7bK4Kmr5qs9gREnzoF/I8ItjHOBHd1VmD8sq54hQ3pLOUNjYQDnOw1ggBWG/eeh2ZyH1t3mROxqtmbi"
    b"tRedCgdCbPi2zxK0bL1r/T2m8bt6yXy7q63e6dhVbU5fc0+INn0T/mdfBEaROSt9fYBi/2WAb1WaFDf0b7WJNQd0UWRC/zjT572E"
    b"EwOZcKlU6kt4wtanTmrTF+1SxigyYX/Sm8n5dL2175OcFxPVZqb0S9ftfTaKTLhqbymROzKECW69YMco9KUZc9g6wZcnHpWvPrPr"
    b"EUaRCT6RqYZweksE7+Sa8+NMNRLXNIpM2P1VYdPbsJp3w3582wXbKDJh/6XkB7sbBXUWtHnPuQQw+uycHSlGkQkcqSxf8oTOr8K5"
    b"fEZNY1CSJ+IJIK1qexvNdTai5sMgq6Itu0zFoquh4TfvvHto/4cH43/c/xb5dzEQs8FgBWj0+TKDmD8zkNewY3178GWf1W5jzKsP"
    b"tPXz5cmTFp+oIhWA2QhWGqDtAlm20Gl2s6oE5P10sSebGTJfGc9+fEs/fkr/9IpZXTxa8PRPvy6z4nJUerShTD8+br4Xj75ccuz5"
    b"1pXnZm3xKEE7cXbr8lcWNH60cdLN9TnrPT/6tjb/ufZ0zWqNHyVoF+ZkhItHaUImHsljE49+rWl3T8qtiUcJk2Oz+ugFC5P8KL2f"
    b"uLS5Omm950ffsZ1aKq8/sPrGjzZMlc+tyZjCR+n9zJ3KbWne+NGXShbubT6/YfWNH6W+XzteWT5tvedHqbXFx9rqgtUaP/pi8swJ"
    b"beYbqzY/WtA2n92oLC6b78Wj9b6ycE+bsnAjHn3H9ui6/lSaF36UoI1NaXPWyheP1vut699uPp0134tHf0xOVSa+lDBJj1JrG7Mw"
    b"V1Zr/CjP6yNt46I0r/Toi8nZKUM4HpWfpZmbvlVZtbiVeDQZD6j1ibr4jnZnfuuyxTrFo4Sle5f1lSULS/zo7LdJnMv60+cScdKj"
    b"tDCfn9GurlvEz4/ylHwlvxePPo3pF+/qc19bGOBHaUZOP5KBiUcJg98uy+/Fo19j3563Vz5vB6ZNL2MGanPk/Ch15u5GeWahPHnZ"
    b"6o9Z4tPk5sZn5fWL+gUL+VaJTFc3cIPujsQOzRK/sTz/Ft5qE19trkoCRC6UkPTZDBdbFc0SPyJ4/kRGlXiUejz+eHPNWrfi0aTc"
    b"YTA+qlEungEQLzFwZDgkXvHDCO14DFuR2ZjtvVGJ7dmzh7Y0jFa6h6U29LlRTPFktMHH0iwUzI2Wj1s8sDcDJopEsg8vaRMntLvr"
    b"laXPzDpqMg9mNQ5pRFJxPvjtb73UGx91xKG4fJLPHRnO+BsnKXjfD8qjr3rj1mE+zmRLAxn8Zvvqip9AryWifYSij8CuVyHwE9E+"
    b"zNVH9akl0F9MTP1oge+jnryYwK+lqOlfPoDxWt/zo29rNZTMWkpqeW1GG1+xcMOPfq1tXTurX7prSQd+lFq7cFJeMeLxRVWnWspM"
    b"LYHvXm9Wyb+4mPYThp6N1RTDNcT4tnSCWrLHT+bXEuPecrSqbPwRkr+6TP//qxx96Vt92uxnYrdv9NOt8Wm6AmMCTw6P31XQeyG2"
    b"+DDdGJ/PxDPDdLC4vHZ9c2WUsg199vJ3ACnOKNGtBjHheKPSW0gbIX4i+gNL3OnHA0YVfM1nx0ToWiQS8ElXrrYHYHj4gf/HHt9i"
    b"x2p9h+A9PjW/sYOCZgyADQ0H3t37381v7z+09513PQIrMaAyk0ulhw6HB3oHIqE3j+ZTEdydj2RSnN2488+HAzu6XsWAyQaRUTrO"
    b"N0hT+nZr0x5vhjv9VP9ybt97B417V29+jzeE4THqE2eVytI90A3MMiNgDaP57J00IvscQXvuUEQxbCP1JA2fMlGaZ4dobDg0cexI"
    b"FOMoqUTGXk/gGEIYsT6iejxYxMcxKzBwhCMYDZykh4qFRLIYR48d37do4mRz7czm2howM+V3h957N/KfBz94XwFpCnx56+SUPjOL"
    b"Z9zXMS5XwtQxgKPNTgMzwBitcDjcNWJgqydfonh8cei6R8QCNSqFIeQvB/a+Dwg82G47W9lPnGeIsu5gLjjqocCsIxBOit+MhsIF"
    b"cUzr8GGggXDjr0Puo1gl48AVdUzOxMrd6vQ6rkh1O7FClxGPVArZpgIrWFxKkQjr/k392gbwFmPDTYkouDVt3uNLE9KfSCb71bi4"
    b"FzqTVoPIg6yFj0+dASN3VIfYLHcRlmxtdBpWho1mnC5XqRb2Xr9xUjuJuc7Kj9aUTIomF+8gnl/WJh5yWijMxbt6RpvCMAlmotrS"
    b"s8rEA6AOzOTEmaQIANWfbNi391B877vv7D1IkQ3CAsK9IyUouXXhDypHIpiJdpTgveXbhZqV+RPCrBCJIODBqN8i4Jl2k3b/EXp0"
    b"jPetAp5pN1matzZ9c2v0illzl4Aka3D8YHWuDeoEJdev9nxRPIRQWsVxyAd//86B+IEP9//mnT9hZFBAv/qdiC2wpLF+/W55jjxw"
    b"W/cuAKMxmZZBLBQIFO9PDMj0gDk1Tp4VFxuaZIXSTEJ+5eZ95RhPJ89wuzhplEmNGOktMKuGQag4j+a00x2JZ0A1rJx8gHKQ7g3g"
    b"HHl8gxhG49/7lINQFEZ6R/OeCCNBv3iDb/GC/ylc1LErwjjsaI5K+WJFIDEe3+7g8fD9EniHD13Mt3Xtsj46BmPhxHeYTVRU1CdA"
    b"5cbbKsrPVvFaLolwOypLd2E4+jc39blJexIMSjCHOAWUUoI5RGu7+0YCXG1mPV5ARfgp51GwhY0al1nQBSE4U1JMb4ZSGEuhnD10"
    b"/LPYy8c+Izj9Dhau9uYHkYHHPOPOvQ+MQEU8wgqCN86HJ+msLesumH2OCzj78U5q34qZ3b3dAFfPtJqA3LfSiVIx01PKHgSOXP10"
    b"voo1OuxfBHEUtDndnw1T1FrBI7SUMtLS5MEnwMGzGJUXSHSiAvFqxw7CIM4dYnAHjNz+xsDtji6/cETXrQmGagEzJUJ3ESBH23kf"
    b"ARexskFRvZgpZsUBLCqJUzYoElZ82t9MCkXyy/cgfD9HVwLwaqlhgeAMKRWUM/Pjd3XdXG7J4LQlgws7Xk90/vmNrldx7B2Bzj8H"
    b"ul4lhIJGhtj+KyI2JKlh8D5AH7wRDL/6Zuj1SOKNHbVDVU1ixttvwgd9pkjgF2ep1A1T9Do2tPMNmhL5CoKaGH2JuMTzGVi/VtBp"
    b"MptO5DB3N90Sjslw7dfbI/YLeJqABgmz4AFVjJ+iqs3Y0cNDiSgTpRRPmutWB34tSr1wIZRUIx6aIEqavFOUce51s3shWoYwkjpZ"
    b"BFYNJ1KATAuE45IQxI6Jcq9adOUeVHIwRWbPx0ZcEfBqEWAkshlQlVXsrqSPhClYOBjyXgK2SeAmMZAFDYJrt/heOYwNvXcBE4h/"
    b"vr65ssAZLP1oLZEbDhLfIpgmFxNdq5IlA8cma6o0ooLzdHyNAwg8zwjK655cU2Or3HqoP3miP8E7Vzn+DaTr1u0zlVOPtq4+0Ocm"
    b"8FZRCllDqXtrXBtfLj98Wpk5xRel6lOT+vGlzed4rWhzpCXS2lEz7seWi4PuKYShWRMQN7E/4nXI4BjHfzVz7BFFHY1Q1syUTzYQ"
    b"g1A4fClmhi81m9FLLWbwUqu4L9lfIDq1AqfqgEmp4IesgtMzq3mFtJrPHk3HTXUPVDWS3HiOFG8RlzQ+D82c9RyRVjeTAgWJcv6A"
    b"ulS+syqUoIs39IU7/BmlCxsDfUlfOr117jJdbT2tnZiG3/ql51JyPDEoHyXUUKSoluvKS/OCkUJQDIHSiduUuylx6/LF+cpN6MOq"
    b"Ezuc/cGCYGjFditp2NS2GvGoCR3AGjjSiLkXrRx0/IBnuPkHHbZpYEaDtPaXUr6YDvJLcViatkGkG+h5wOis9axPXlxXdXTAma1y"
    b"RfLJyTfb00IddtTqHnbVqcP+Myw3BQQyymEFcz4je7qSSTVhD5u6h5toZE3ZRO5IUzZdBJkOf46ms014AqIJe+ecxJ7AMWp4B57Y"
    b"6xqJCOCRY4zukaZjCBr+dA/DP4DQEbJojw0cwR/HEKThdzAZN92hQchEFyNiCbMrD8tDsYxnPpmjL35febJUPvcIk3x/tQqP5bkx"
    b"ui1YpL8DNV8/P8FJiSvzn1WmjotbP7GdSPdwhEaOqgkONWIbKnoQnON0K+O2bKUI1emG2IlQItQeI8X2Rfewd33oGuIu4LhO1rsy"
    b"D4LQHGhwvkRvj5gVHiROgg0ujtobML6J8GwFXK4qdM9Jc+hDGd7mi7tHNi+UWM6co4EvmKPFjHUs14fLpPDkN8K82p5RgfRsmWZ8"
    b"Wi7d77Iswv35VCmbbsKXss2QzeT4Pp90v6gbh67Z6zcNZJKKOOXnqpiwn+4leGKAnAQPP2BVD3PnBqxCywhxqA1Sn2gpUdx3eWHS"
    b"cENdkTun8O0r+tSnmNr29cQbeC2KJdrQaKk5Psm08a04kMfrLm31LfsY8FMPDjP9R3xaoTcSPfQnCrWnBQ2wGr2meqAzpT1mifJd"
    b"M4IABBbZDD3HpCCdmecY3Qev4DWfa3S4qmkbQDLbG6WGJAPU4/wfgRSBmtxNb6uTbpDCQXDCa0aIczQ+ZwypDZgZbAL+WEdam9RC"
    b"kiHZi/m8WCLreEe1qSs4zaIjPs3x5Kp0Hyb+8h2VoAJPaCM27zzODan1KFEVbeW49mhUe7KoPfuUUz832A/TVmEPyUQhRUTTqBhF"
    b"7EJwFPJRYD+mUo2xJJzZx7zXjn1BOMnWQUMeZocwLl1UTaafOW+JLC4g+7TZ6Mc1Ma6GbOtim8ugk7vfFap1/FVeC+Tir6N6nWRd"
    b"J+lWo+NAYMS2kYAo8dZ2hXAseqq5LGjR4yTrueJQufDwU999Nho6o12dgaPC0+mpbxrHhSxyMdusYsVwHbvtzp+5BLlNmJPskry4"
    b"dO3QA8uMMXzPYN6wg5mVP9me4S1xuuLiaUNdHtLtmBcCwba5q6rP2CfVyGJC7/nM85H6d3s4/YOXdk5gI7YdZVK53sQcC2y7QGuh"
    b"kVfUUjfmhLD0vZrY8cq0X33E/l11qIvca1NJjAyC6ih1VlI/6+/lz605Ivf3FQ2SHPBQIPFTXz5vaGGuSr0tvKJdL7zUM4e65frG"
    b"R4dyw6Zz5k2ZXE++KVEaqqsHpGl5alDUuX8iVclfU/px6s8/g4rTIGOYMrbXWrq+EkngnWIH+CNrJmxxBGYABYcN4G4xRQ6Iu7Rs"
    b"URU1V7ZjxqUmpdwvIoGPI+igvo2p7W9IkY8yP+i77OGdIH+3fheHurTRlB+0rZ1OoqFkNjPQnUeFEr/v8lbnCITn3alCe6MKEmXa"
    b"ofokbqkZoeHoSWFICn+p4sT2j7eolqcdByMHbHAQRvX07F7RGpJYQHBUhdR+44KXK/r575BSF25rE5cbbKAAm/aAGdcaoWq8dqQg"
    b"ED4LCuoKH/JU9h54xx71QeXVdAFv6YnJnVDnKhWSaTUyUOrOZpJvDnBmpyMjr3C2p+bWVxiwTe7zWhPJjTC1URizleCIqglU21g7"
    b"JU29J9DX135MZGrZkUntgBYcfE3mr0ZKFysRj5dtKXHWgCc0i0Wij7iAuA8GbbClK9dDSkSJRV9rea01tru5tVGJASPeqQR+Gxjx"
    b"SZXkmaAJqLRLMEGetLq08h81ff/LpsqcoGQhDbija6ENj3lneyza9ePmg8WBmA1oIWttnhSEkUJlRkRdewBJobNJXLe0HTTXM58R"
    b"3MMaMaIDUuLuBHfarwbeZc6plrASSmHKyNWLBhWWSexa8H970FxNnm3j1fh9yCuZZ05lzonaLVbqktkmvm5vkCu7eCOhMFXqH1CD"
    b"KUyDSmExCTWZyXTQ7SV2CsVPGo2xptJqElQc3GCz9kBSnnRo47J4Jh64LJ12dzNZPCFfjcf+2Kln0G8C0MF8wW5lGfNfZ/I3qmbP"
    b"/OaxkM0szkRwEmlUWc1WnETkzXS/ESZhQJLcfD9igZuphAdgaOk4xX83itXd5ru6GTVShjF5WOYa54PlP8csDnpOYH93sfb0URLa"
    b"VLx7OM7pluUl7rXTQMwNIAu0JU3O1tneEu2y5Y80kIO5dpHKnAqldYMzKDQr90SU7o2x8pXPOGluZf42xu6tnsAdsiffVjZO2vOW"
    b"eeWBdoWLYPBcqpA5mg6XkphmUo0EDN2s5N2fhhqevlKj3VVtdIO97tiPktkNH7+anUJd7rWP9jEC/N1sxB/qEuc/lsbEjdZqxJL2"
    b"/+YQL4FDmEHXlFIDJIHIluGWBZRioxobEVclHAsIdg69pgoBg0AIwZhHDwUSrnMqiGEN6JZqPDbYU93BdEMxEhT9PshpJGO7MFNG"
    b"vlB8a5jOu8AvzqvHafhIHlIB3bqL7TKO6K57O8GFcYst6CQ6HiiAQJLtwLFJIZ81/NRGntVjgQ9cef7s+UjqjOlTAh+6swraIBn9"
    b"FUvVKwUr5tI1F0gyn0IugTeqyKke7X49X85bfaVlKQmrYMj2JI8yr2z0yj39wsywoeYGxgsv03qWa13L1lq1nhzVWIuclgfWIuXb"
    b"ca9EKv4pBXp//mgG1HEh1//iKdY9zaTEQPux/jqtpP5a+6QSuvsNoj2aLvjXtdAu6sN0S+D58qtCULwsJIrGfLvZZ7/DemKMuOwn"
    b"nomXLQBr8YQqU4ZLT7KHDYbZ0RJ1SkvvsdXQ0mxY+Ocng23NNiHGPrH/YMNYzKk4k2aziu1mLx2KyDpIFqq8C2Je9eHEA1mH1moU"
    b"sG4ghdAZ3sT2hhdyddrdnCG/OwJzav3+TfkommV1VwtFN+o4TqC9mGkOKK7bOjenQx3O5QfUjOqywTlRGnB7yoCGh3+efKNP38Kr"
    b"Mg7mS0r52zVt9kz54RKGfs6NKsV8Xzpnlwdx+jJObzzOvnH7/NrjXKkRdUuvu9zHc7w0JoToRbEMxFKUpHTyKa+M8Pa2Lc+N6Ctz"
    b"JF92ZLRmqBH+kcaudgK2iDwHCsSGTS0pS9WRUFzol2mLiv0UrF8o+oVlnl6+JllbuKjNfKqfX9YvLSl9g3h71cV5sEQVoVMrlVsP"
    b"tY318vm7m8ZVEtr4/fLDywrSJh/0EpDpkPUcwjnGyMO0k3RrD/x6H7DmsLnhdSnZrnTiCdRGzo9pPsG/IyPbVKAtz0AtLZc0bDAb"
    b"Bk2LwVT6R+rWtIeaaBqaeBLbGe8jrmNaXopxDRcjmk9qJqcWE7lkGh1zKGRDtAGCkzM5oU+OaU+/1SYuVm7edwQ+mSfYgrhfhtpm"
    b"SNKjU0wF9oNE7C9JeftFpG7ZwcNrCzo9JAoFbAOdJOKkhqzB41tDlzH0ap9zNSbETNHjRI1xr4KFIbzYCQ8bhmqo8oXEoMMiCMl5"
    b"8T3lEN9z4nbpOKqV8GaRHK1z26U1dQkt2lk0JRb00rWB6LVxaLRonajm8y81DjTRwaecdZHlR/sCYvFVc1ONP95cvyxOks+Nli+v"
    b"aevnK+tfawuX6KwpOm30swum1wpDe06uOtvE4BhojqIJEK/4N/Am/Orwc02JoGeqw7eO0CIwPGba08eVjau8NU2tntZXVpSP9il8"
    b"C1Vk68EU9Grr+Hpl8Y5Ns/A+COUiGPMAVMkd4lHduLN8YnZzz1ZECmnIeXNQfd43jn4Q3jbyvTW+iLloOvFMa9HRaamH7PixB4eA"
    b"AML+hvBa3xbHDQ4W3XlbnZzDFg/bw4oaKABzt7SM//ndO+/DUtm39xAl2PfOWvJJKTOUyflnZU5lErlhzsXnl0jUno3049LHct6u"
    b"Qx8caN4VtZKk5AfwccSQ15xxt+6Qvzri/YwRVdmP7M7n+1SK1R/BNBwgBKUTBLTQjuDVRWaM5zYDscRMxQcHjFudXEFxYthV9JSa"
    b"zTkH9aZqt/h5YGRMpjr8RlZ3hz3f/WNOLFQ7CI0zaz/mjG/ge9cpZqcotB1/RjCdf450vRo5nNpJPw5TSN4v/8q08yaWB2y5anz5"
    b"X6b/CLXvH3xmcEP30ekgVHTEHiM4OfY4UT3w2NBnzcB9YDb0gPfFNL+Y284dekZ48OCttV1y1gjNIDKzxIotc468Pr5sRhqjCGoU"
    b"16ORhtQo09NRpCd7xBi0drTTGLB5YbVb2JmyTapt1zuk+5yO2hYbXbNmbelSynBg40YicLutaOUPf6ksQ4Sheu7kviLt2NiYBLZC"
    b"WxG+vELqbV18ffus7sX7Vq3Kz8XOqmjsFm/DLAR0HXwgIRgNr2w3ZzPOBcjU60xPFQzgNaEcbID87xf4T38iky3mXWd3XGzAxp9e"
    b"kNW0OiIzBFPEUXod3zCadDJAVqIc3OCFeuAaJUwdUqEPc5PboJqCH2Az+GwmYorwrWAShHr1YwQTaqgHQz58GQF4MOHO9t3Rrn8S"
    b"TiwpsZ3tbVF5L/NPmVIur7z11kGlsriqXbtK91BN8BUrGNHW3MJBtHgklm67xZupDiRyf0x306WKv/9NRHqC6hYLBaBgMB5497/j"
    b"h/b/iZXhgP7Z9cryLf3us82VNQPwGGdawoMXle8/01dntTsP9NtnyRyjd+jkO/e4chGzIMDX8D964YWDAJhvW+cul698xqDw+t5z"
    b"S/rU2ObKKNhYlAuJGq88v1o5fU9qg85vaM8n9LnJ8rn7+B11lTsJy3zvu/s/PBQ/uP9dSrKUyhwN9wOrxDvd3gAL/ij/G05k0wUy"
    b"6R2vjReO+yodcFS+8bIarN5d8lsr+Vx3t2pd12u5NXtpk9naELUtMeN67XdBbpTYixT4pLdp3/uNn/T++i8d0fAeEbzYG+Y9uaDl"
    b"IiWHr9Gi6WuUqa1XdA179hINDR4BXeHSZTtNtG15Bpy/1N9E9kiTcWbYZ2UZrjM3mu2SEF/7yUB8V/s4juAF8t04xNn4lqJaR3PE"
    b"+Q9Zo7CG5uE/qwYFv6mlo9RtojW+FBR6v/zH2EPZjMsgKmXDRRBbiRQ6PWGZZjMB+/W8wWzGbpA4nPTE8CmhTj/eS8g7sTj5eDMW"
    b"R2O6vieJQHsqNSRegoL1bd9bfEstdX8MxfCUaJTYGRFgS1x66zbhEj+NHhMo35vBHLeIZY/zOz4Gn2OACeiyXYiLo6yy0G2sodzQ"
    b"yXpx2SgetamWf9Rqwp4GjTOP4tdZS2PZvsXnzgpWRywH24Sy0gH/Nm5HWTDXXimXzSf74oCNeE+6aHIyZAj2Qzm41wK6wvztrXNj"
    b"W1dmQXYLATt7hndiOLkRpf6kjZsbMKP5vkxa0S8+5mwBYsfmzHWoKuWMqcltjM7INzXXZj+C/KoKuMDr5YenMQyYBveG6fnFLrlT"
    b"0OIZDa8sb8wimoxEbybuqqdyNcFl+gfyhSLmS07l++2xZKl80rghidIN8adke2EZuQOJjw/wZUsOYRcQWgaG/xD0cLI3n0mmgw5F"
    b"LkRgMkAHmP1rOG59ZuYxQrXDjWl+1Rn4U9OHfN12OtX0R1hGvMv4p/fe/R1MqngVcG+u1rWThoVNHPrfJKelbYpVEe+227hF/JpB"
    b"ML3eN37/RGTovy2L+zcNToIwopahKfdhOceqFD2uax0z8jEZbodEeT/R6TbSZFG6ysLUVLdtEoKrOthtgr923GFOdn2W8565P7JZ"
    b"/omsw6fpm7GxplvTsfkVoNjlDCekJhYSKVoF1YIwoMeGRKBvQYQoKEISWUuMQgnm7zJlaaihKpz6PxUzHzicC4Q/zmdyQYJDPNCk"
    b"hl8ovHm109rSmp3Qnj7eXFlVaNNLpiFzx4mietQ32yORzj8fVg8Hdrz+RtfOUCf8PNh1LNrYEh1504QHpe1/f3al69VgZ6Lpk71N"
    b"/xNt2tN1rHUk5LmKs4n+7lRC6e9vh/+b6x7xJrbpdlrlzXiUE5NR2zRPd65q50m7l5YUvjJ2BbClHARGnC68ZOiUvkmADvIfI6wO"
    b"6Ago4O00kkMat5/xQvSQl4Zs1s/kMkWqZhhrHbbc2K4UsTzfUhiXMPEckQFcSiQYIuVKWH2kftlNwIb6ssVyw9J+P132XkJV7KN9"
    b"b+NpAgRrnIGIs7ZhBTua7+QXITuwv5T4tPp/4V8HSHr3QlDxYtTmFsz1Tj+kiJ9fKP35VBqWQCAAr5lm9Ps3tWczf392FQ9y0Nh4"
    b"C3tz5Qty3VzlnuAr7c6KNn7a8VoCboj9UrKRvwFFbPPp9criHSzbKeBE8EGxHvDuSFDHsOWdooWZKe4VNyLnipua1CZObF05V/76"
    b"njZxUp+YLZ/+GnSoyhKmzyh/87x8c5ETfGPA1tgG9FVbmN1c+aaytMSJLjkHB3YBWsfSZ6PQMGb7NikQY1covm+IODrFKmAwo4l7"
    b"RKLAPNDkIKwKL35tpTLFLaZAo5zcFHrnKlOMEhHP2Mg2xJCDALHxuIiSs6dfxZxI3PdXQHcrkR2CyB1xbnbIUMhliZEIfnB4ouoH"
    b"xVMYcNMkGFBZVCu78/ls0P5lyJ7R00ZgEx/tU/SJCxZ1yHNFYHoSajHek8kW0xQeJc8UvqKQDvR4ot0bo6CJzbVxmfgD8Gwetykv"
    b"XN0aZY/dVbkn+uxc+btbEf3M/cr0rD52FsSS9mxVvz2qf39aolDuo76yoi3eArMDRBrmJZ2b1k7dLD9cAvoNaNPnKxtfYgKBrcuz"
    b"W6PXrWSAY2e1xStKNByLvvdWRMX2nz7WZj4vr27oo/PazA3t1A1Yu1Jjsba/nTgbCzf/MDrW0gw/m8Ot8LOtFX62htvg5x6s0Bbe"
    b"BT9jzbvh955ws8LAMeuMPjm6uXYXxqrPfa3NLXNzm2u3y7Mn9FOn5FEZfeYuQ18wi/mdK1z4w+iniWQyne2IKtoiZluvfL9cub3C"
    b"w4dh0Ms4mylKZfk4t6OfXzayqZtTyTXzOec8UrkxkUakh7H2rPgdMkh60HVB973mxRkUFzEW8kNIie/mk4nswSJ0q/8AFoVNaRLy"
    b"l0cWBOGboZQUQ8FYo9IPig2guRE6U3T0XYweO7SnjVn5nrZQqF5Z5NXonjb7qOJ4mUg8mUj2pklu4bx9tC/CBMmqFaebBGIqP/tC"
    b"W7ikHAPVvF0JajNL+tmFRrSUty5+p09826gcOvRuyMF44irg2wGfpzhAWffvAaEzeQS0iTtAyfZG8GupCRd02suzQzezcDiGYQAW"
    b"AeAA/FhfBrMiWJd4VGkJLRPVLtkp2TKS0MF3DrkOHwNNYEhgBrR5NeR6JZloRAh0ZJcKHEIh2cf5Us3w3U4Mz+8akQW5M9RNteVS"
    b"wlvSSbVJ9nkEelNf7D6GLjLi93ED7fDZiEf32aHUgW3R3cfoA2cujBdmcI7orfNz2nHcLCnPXdcXbleWnuiPPgUE65PT5n0Obnol"
    b"RHcCXNxOxyawwQZZcXw/0e9SGXHYDjmHowAJNeKZcss6KFkLhJBMPmBk5aYKKL8+7PT+3qjA4YKBBmHpWNq1S9+6Yi7SrQdTlaUx"
    b"qS59/NG++MEP9/HeF2USo2s+znwlfvHlFbQt9fW8vkBqxubqlLY8Q5tilFWTflGGbPqCcmLzt7hJZ4RANpp3wrMdfHD/3g/3/S5+"
    b"6J339n/w0SHoQCxKKhnLRZGGe+aCNnoZ5Kc+uoYL8PIs3nMxf1aIm/FbmPWZU3eee649O85pz/TTF0BoaI9GqZ0/7P/wnd/8t9xO"
    b"M0dU4+VVHMXoAZpKtBPjUEE7uYpYWP68vHiRfzDa/wOYezGT7E8Xe/MpkwzjSKbxFCwZeZtLeB3LJ87pFxZwUojGI0z5nA26snES"
    b"r43BOZvahWnIt85ehw4IXyMdVcbbQC59oy/c0hfWUIVYmtG/vrl1fB0GrK/drDweh25Lnkg5mXSmPx3Gf4K45y0dJMCOxku5YgbF"
    b"YTRUdWToibVGhjEKSbWjJRoNuWLzJaiU+FtqfSd9Zi3bONg6KGkS3dm0sOPs6XPQWWsoRoA53u/U5x4APvS56wCvcnxdm9rQZqe1"
    b"R+dB/Ybpqsyf2Lr1ObzicpYqIJWAnKBw39vvg1r1ncjEPbMESoesOLD0EjKhrRf0DaQqKtRmHohyoFWeIZ4SXI5rc/qpC9qp+2AE"
    b"6NdGtdkzW+c3oIP64wmYX8espHMcc2QXszQltuxywC6wKqcIs3DYhKWdsS6YyiD+au4yAkbhKaS8oTSzndqmvKq0tNkmSKIJ/DJq"
    b"+aTyKFBon8ZfWTHOmwnTNYz7SHHKhKYGyZXIOVtiLslDH3pImaJI26nKPTGdnVmpqVR+MIcGO7r/4okcyMMMSJuBQY6uwujgzkCP"
    b"9ZPThUCBcRDEbVLRgMl6SGXZxjfaUkmHiyeyaEGnsvVqVR4YdE4xahS4IoL5vkZ5ShvNuUJs5UU2M5w650rO90lrh436msuHRYm1"
    b"iCY2V85gKDdr19rS0/L8Mt9a4F5d/15a/4ClRfP6s60ubu3lLzAwjEkeo2H35HO8L+vrm3YSQUlI9w2C4BJ24tyk0goSunLygf7Z"
    b"hDbxBM9UicxkU5WNy3i52tyY8v9Fw7uaYmqEtYPqS/ufdvW6122jgoaHffWCjc/aHupDX54GWxgWrLZ6DlOaGEvaQ+Jz3x0MAlcA"
    b"dhFbIRtA6LDcYf5Else0YqwO0wZtIke2lSp67XWe1uA7Mxf067P6tZvlq4t47A04TkQ4NBQ58yEs9BZj0TMTQP/dG6yltxtn2ERX"
    b"+XnEb8lbZh8teaNf21j2sd3RaD2L2rWCi+amOhtZzlUqnAqcwocCLfGMG+95ih+YgsVra8fYy4D557taYeHwLryiz31dWX2oLT9C"
    b"o9mG1ClWHcF4ZsrBjeEZPHmKNxjCqlz/AugKrGHtzJp+6gtXmzTJirCV2iko1ZwDeBrx3K5Cwqo3XyIRoXROyvD00eRIZ7ZcpOXZ"
    b"004EZx4Jds07hxbRLCDdU660gHfaL7xpp6NaNrVaqCLnJanX6Aflk3ky8qz35pCpzohXbwlBZtLpRpECOVSt677ZSf8hA6AbGzK1"
    b"0F3ljP7P1VuvC+CsDvrsYf98nawuveperU422SlGQHKNoNhEm0uCURVZJqQLmZ5hRIlNIHBAO8BPsvihXVwWb2oHr/iQU1o8KJ+/"
    b"rK3cIx99xHTOsztDeOqufMbiBFRHCzb65iobV1HBWLjLXg6HHgsmIugZssygu0Xzhb7gUcdSSmT5HICpizmlHg/P72CH8anHZn8f"
    b"rmVCQLsPtezssJonYuiTs3M4AtGolhuScb2tTZGRPrPQ5vstTlWDQ/yMztqUkCVMFLu5tob3f3MJYRhEDDpJSKPf1vjxfYnPMnsi"
    b"INTZ3tzlK0ksPY21FqCzKuLCb5SemMMoOuUQ+cgPgD65fyidLBXzhWB/YiiO9IOxMrE2kFkqLFB7m33p9ABF/KnovQ/jtWH4Ba8N"
    b"98LqPMrHjhoZUZ9kBoK8iBAOa21d7nVXStZedj7rDPWxl72sbMqnzBq8e2f9dLIG90j7M0PplBisD3cxApnsLr9GRZooGyoqTzDb"
    b"gukJpI3bCYqk3ZobRQzF1UwqijeKVRaX0eGG8fqTskWrX5zXxq7o354H7UtfmtlceYDXB89+BuZL5fsnFNP/oLy6Ub5/Wn90g+/i"
    b"goZM3+Um2D+nTunnv6usL7ITT94BZ3MHLXSycrTxR4B8hgnQ0AYnL6fhvZxKqHG8Hz6bLqZT6G9H3yVa+BNgt6P1RP5Bw136WFt+"
    b"Ls8cH4OTWA3NBzrvSgNoouQLRYF+aZ815OEb5wgJnkZ5q31pBmiMRyKbLmAT6ueXt67MyPwFSsQu5a0vwdbHAMylGfEKZgbsyaXz"
    b"YIkDQEPZRaetvMFobPkLR+7sFNAw+ojvzJs7+YAetE8Xp3BH9fx3m+tfCAzdmNbPwCyPcdINbWwGXb5WtDDRmPBq4q9Xjf069BIQ"
    b"1qTF7StncEUYIoZ2NojfHRVuWaQ7r2t1pShQX/ZtXsHoa6m8BDlXRdbVw++3K/Nqy71qCKhT/MnBxS80oh8hxV5IklXtsB8yat9p"
    b"7fVleggmuoYcFH+rbHb3lDgSEsQh37tiSMSQ/citW3nqoThIicEFEZbF8sVfD2R5Ur+R/KYnXEirmKPKN0KyUP3ybo8DvQU3rNo4"
    b"t0XQ1v4EqyKfs7F8Zl/6qavKIcbG/kIhX+AkVLyPhRtM4/Ny+pAevIgs64qRC6u9pSJ6BIODiUxRpMRyObNK0vZrRv0Deip/ky/0"
    b"J4qenmjjIsVC1oi0CAO6+JzCH955e/8H8f1/OiQJ/v5ErpTIEtR9uGp9ggFZXzO/ymIQBoVfiE4MJAqJftU/iNC2e7q5skbR/Fc+"
    b"2scbqB3iWIC4cOkqx/l0xHbDu8rxx9rVU4BfNrgxudfKPZAnIEw46sdjr3Xfu3sPHtwvEm/QdbIc6v7Rvq17F6BpZPpULM5GBDhA"
    b"KOCZO8kGIeb6VKTsoKQbUsVmV0WRqqN2Gy3uNugaY1cbre426KLjOtrY5W5j9YG2fr48edI9lDZ3ZboFCzOJ8OSCksszKW4MxuuC"
    b"eXs7iJ6UkIKeSTVbOqLol25oy5/RZ3/84Le/pQu/39t7wLoi2cx5YtyUTDlNjMuSP8nnjgxnfAL4+RblFFTpZ0/fLvo+ky0NZLgA"
    b"hoI1Soncx0cDIw3yrit5czggLV7ID8qe1w7kShJtY/D3b95599D+Dw/GcRB0qItUDdrf8rxOyziiZXy2/62Dv9v74X7XeqFcwNhJ"
    b"cdoRQ6KMySXcUjaXRLaERT2dRrUujyk3QfElvxatnwUF2QEGqlQFYV5TbFIA6YnOzlCtqoCM+4vNQc0ta1OrDjhUqSoY43ZjE8zT"
    b"7zbX1h1gqFLXiGTQ9eb70/s4L7aYX55xj1AWI/jR6aVm/w+PtJ2rWhxnxKlHMngP6Q8UhuypwLf68Il21Eo8CJHvX+qkoXdh/mFz"
    b"0j2UChX3j/BbEUmU7DSXclc7N0v3h5ktSuwSr8uTqlNTJssc8TLjoT3rgj5ESdqhqlYL0hIfWEfeLJ4j4o8cbAdK6Zecw8k5IQLo"
    b"SEONSRBIsoeU1eqxK8Krbr+xNOe+86yGfD+zcCTonwOFDernU+71pMY2l4eRkQqs263j980UUVEpe5QcYGu8jwHPH9lGP81AZHOh"
    b"srv0RbqKh/ovz/p11RbKVUd3BQHIoW44ArdWmfWP6VPNg+mq36R7NLM9Hq8ax9xHuurpGye3CvxEnZGymjm64+I84neDB8ewsWNW"
    b"PSWe7FYij3F+dHaxu9VJQ2001Uk8cCAplJhk7+YU65SmcikcF1OTvNUHNbWZz52qpBE6RafjKObM5gf0TmBgeACnz6M+NHMB3V43"
    b"vzcvEzU6ScHq6FChm4Ar3y/L+hF002C8uL1fWXyu8PQo8Bn3eGvtUmXxTiDgDnv0D45zJHBtlDl1XKTnNa4hDb0kuC+6g1sPV+XT"
    b"PhTl631YSB5CsRCECQuZgk9WP72XC8C0FCyDc8ufdRpAuxRzF476Krb6xVuPdaumfZsMD+QHgtZqJN3T8y5jaxOySmKNbW/OCsj1"
    b"3DvmhW3vofkRRx0B9I6AyFCDR2cliLaW+PR6rFnSAI0R2bVAc2DMtTxWdHW1cCCfx0CfTimEOtPFyWNlRQtjgDGSyCyjql2ObSA2"
    b"RiMyC2PvOectZnamn54E3oI+Wz7bQml10cH9/RhzHrLB+JZBbeYBxidT4DGCWXwscmafeyqfy5Fbx69mMU52c/WONjOpP3kCZgNG"
    b"O3z9tRJTtEczIhbizhX92l3y2F/lnsKHmxvX9KkxOrKPrniH06O2h0ty9CJeQw7vrNu9ZYbUWHwaWLQ0q8dG+O75lMjgKlRaXqVi"
    b"qn19jaQMYkfs89RdSval0Tlm0mCj05/q6RRLUVZj3OxGp4/DwUYjscdse1+ZSZ66lK+zzNcdZzjFodtqbc+cPUufWt1HerRTeNS7"
    b"TAaf8bJR5Dx/NUAKHJtJ/Hw05Pocfy7nn69nrh7vnCGsnDTlhjTYm8mmjaH4+cPVoreL35iBbpyBqjCcGUS6SY5EQ1XvO+2u5fZW"
    b"TYdrtzcg0Se+l71YhyiobzQ0El6ZzpY9rxn21xit3Oh4wGvgCAqtWEiUJvOlXFHcqERxn/B7D963ZGR9j4442KNjN1M/iwcNeNPQ"
    b"3IJ0bxq69wnF1qRxlEJfu8kblI7mmKmKA4xAYpX1dQR94gnG7Urnqn4YHePe8OPW8fXyV6usX8baFO6Z8n8vKrFmVTG35EhEAFBg"
    b"51AbQFTujemTp7VT9zkkVN4mFaOnzVL91ClxGnBmVptYVlqazcMcqHrzWZLzy5WTD7ZGP9VWz+FhyeWxrZuPleaoOMTIQ+FoVUDI"
    b"1vqsXa7jcsCTec0wGSgPiDE6d5yt5M2RiNLmoPR8X1xwZts+OW9w19jaPlq0trNbmkMNnvxQNOCmQZUuOjnKepy0ydjgwTHNNKci"
    b"/1Zq5D+OHe3cwcU7ukYCfh8ZKXukL5W/Ksd4a3OHVGNHo7IDL5QRBzADyl8dPXEuGTGuutbNnj17/FbOHvpvpKH6VmzRETbqve/q"
    b"ZQfWtlt+Ssujbv3bV03+6RVxswUKePVtoI4bCWvA9ws8FA3Uc+VTjRZ8vRqiiboymddow8qc699O3dl1a7SFHiTfRmqnSqzf8HIb"
    b"SNWVJXf9XygeJ+1B5rH/AU2L63RE+eINK9QJGf7GQ75bBU/zd0TpZO8ohqlXls6T0AQ5eGJz/QTIQdkGYYteHqXNApO3VrzXaqOx"
    b"oDjC2c2hhStAygJipRnwn/c6Q62IfTnSG7iCrqr1hv2lP1eHDGes1CmfpNw+4gpTbpGc8pNaTs5tlyzmFZXbkCdu/x8fZsVQSVIn"
    b"4JGd2nzKEy+otc61ehxn9XT6kavLyNMpufzs2TqlwyPkkxNHAMiXaPRqAt3WFNcHChb85jg3x3kqX8lUv1QSmBYSyTPFqB2qn+wR"
    b"gFju1AnHQ8IIMP73YbuheMkRAabKBY5uOHzSwxNOlStZ3XDEIRJPQNXuiHZD6vcfWf92RuYpBwWgatdauCH5SjvDgVYj670bolum"
    b"CVC+KW+rZZziD+xeOvqOcg7i5x2YV6ReBx2GKMgpYchoE0wCnenH16EcuQWHTpJ5V9k4Sec3pSOdIpqSTgPRqcpLbM5wECOWnFnb"
    b"OjktB68a6XEm2G8HAtM8b4/tnZh2GI9oRAGzMkxLm51oj2KtbFwygyo3V24BK7M1ili00vqFvHcya/v13XPkfOOvgdd0R9mkmY3n"
    b"ehPK9jw+tf3H/mqPpzwkX7LPSOr0ftnyqqJn2rYjnshJ+CiUcpjmOJHNprNBCnCXjCfakVODIbDIaJIblZq+Qzp76WEMU6tVrGEP"
    b"2ztENC0nDKB497IRrV6+8pmf0fy/0F4esQUip/Jey6j+xea90KovMs8F9qKLq4oK+GNUwXomxQTygnPjWGHbDMmtj1+458dJEdtb"
    b"vqm899odqZomxAadjp8DI8iZi9axF81bRpPz8C/UovohkD5GcH15/qx2Ylz/5iaeWFicwpMq47c219Yw/xlpyixeZI2Vr1l0mpbb"
    b"2tyhXsu7O3VEMuMQ7TdCikuI695iMRDUsI0tFV/5xVgwHNXWbspLCU7+MVHD3DEPY4nTc6H9PnoFYwn4RkRONEYpV5WdmIAMc1Fy"
    b"Ogov84hPaNqVs0ShkBgOuW65pOL6vXnivHUHfyefBMc8uv9hJtvmeu3uvcut0TE8+HLmujZ/2n5S+4o4qU0nss1B8yD5NCQNmtwc"
    b"Rha8yQbnOVXvgLHtX+vMA6hytzPfvozUz1U9jye6k1uJk4TXvhQnfcRArpTH55WPEwUKxD1QUnsVto7La5cxH1xl48uIdnFcP3Mr"
    b"wjdPKpsrk3habXWj8mSp9i6LlK6ef9ivwrGV1bjf0REDhh9gaoieQr6f4k6ps7/85S+5u/CDO7xNcJhADe9d58QYvzzGPRwBcDVL"
    b"MKSsOj0z/+8uZbIpdKUHjeGbaBB3bdLpLvnUML4UJ4VRI6LqRmbR/6Cb0mu409V/UXc6nwAvJAbjIj/59k/Xe2YcNyA6s467s5hT"
    b"KIDnmSbzOiwpMTnfK9EbE5fROF+IWwRDnnddkCpoNhlwK0h8c4THiyQzXO+XAqrP8V26FsPVTzxQWMqmm1CGNmGzdEuG55DClCKn"
    b"KZkH00Fx3xkm58npP1JlA95+8YZ1t5XtyivzPg7vNnI9+aqjgffwT7EAj3STUpNAnO/QYKGZVTybtDCPwH2nlXrmNa11J8WwGtpO"
    b"agxxtwcjV4BorNKH6pkirD5sJ1+ErQ+OS6SdmTbIXSinZDGTtAiXmw+LcAvfbQlglxCunfXELomNLA5VBi+jT1Rv9EaHmqYL0bu7"
    b"VSUinHfww/K7gdA2c6mysqYv3NYmLtdmntvNouHde0NKefOaOu6AeGHu7H3pgteS7231WdO1WLN31JTg9L2+C7zXl2kbKqp+7fjW"
    b"5VmM2X38LV3xYM4L3WZEN8fw7eO2t/4UaE1IT6CydFf4K+dGK/fGxC3m393TZp7g0fOlJ9rcfdpC21xZ2AJFdn1RIU+HSFdbvwa5"
    b"XQXPvK8JVZgX0uvA+CjfWX0hLS6gzz3QJ59rE8uyYv/LHMz3i+tqHmvCrbBVN+rqi17fGp3cunpCv/Qchq/NTuOqf3J968qMNjkP"
    b"j2CN4dvzy/BDXxnXLy9rq/fw94WTm2uPtTvz2vKM00Lz8Rj09BfjauaTdFD9pNrVDeonJOWA9D/BCY3Wne0av4va3PGf4KXqsehr"
    b"La+1xnY3t3piB90+n+AVk1a1cKxn5LcBJyQlWuP71t27Xmv7f9Vde1MUVxb/30/R1Wo5hGEeQJBQwa1syt3asrRMLPefgZ3i0Qgl"
    b"4DA9bOEaUmgEBmUAExFBUCTEx6KC0QjyyFTtRzHTM8O32PO43XP7MQ+Mm2yqEpzp6Xv79r33PO8559cUCHUNn3aX8hVFfKMnz0bP"
    b"nD+N4gH5uXRbADN8e3o1X1yNnNNbWzqvhP21w5GTWquPPtcNV6lVftO+OhcKnww1eDdvacdWkbOx1j9ZTVvarcbYHNrCkE+eLdZF"
    b"7tmzFv2jQmv9owjugsUH+fUl4979VrOzwwrc2QA/eXfzD6uHiBKIttS0SoMQ7UNhpf4UjCXUEBgaGiryQpHCSFxdcDeRUAMLRbl4"
    b"ihaL6oNdXT1DZqodC2ncg80hP4lsO4wIeqooSdaiBmNmKofW+YK89zNgwT9eB5NdhVVvDMWU/2wq4UDtX1UOOMBmz+ewpsfmjxiY"
    b"YLY0Nl7iUex4ylhNGTeWZWdWe5uuyfg0LQEZa6bWXz98RAhDegeBhGuWtOevBc/YgAPqq76uNhT7qjbcAH9pwF8dxwuR+sbWyKmL"
    b"rdArPr9AZwN2BR/2f9+Afe8PUMob9niW8oBP4ejwMfS18ZQ6THp034BAuglVBQZjMUwG9yvSRcma7BoiQFMCFxogUecboACKAatQ"
    b"v/TmVS4xSNTPvLTAZ+CPPYvkXw6WAU+tRrmGKwhkPCy7Fx2T2BLwOdekChfF57Uitqf2aaWe2qdZKEHmHA2rpjuJmGx2eZdQTW4Y"
    b"L6dh050+9ffg6bP170Yeye4h89S0a8hOAJ09OkoqK82AhIoghJ7OIYkaBvucacawQ1k48LNRGjQrhJA7YrlmsFLnwnVje5pUgGQ4"
    b"EDiDQQ6TE0JAJOfyD59wHL6jqM67u6NK9uHk/tKK8f0rLpHDlPPLyEx2cc3Y+BndwLMbdOWWsfcdy6Hs1o/ZB99ZMBTW0PAAaGfe"
    b"HMikNONmjOsu023QIshgduIput9I6EkNahRj6gGmFdzczSZn1OzNp9m5H/a/v2+kxpXQJ7hqx0MNp/FfWAdEZeHhZu+u4wUKag3X"
    b"otg0Rp8wJ4FulHp7NGsNZlKJSZpJ8TTmFh9gq+lNqvCdFBmF5EQ0pteI6Tce54XHCaOulcbjgUA4VGd/Z4V6T24a06n9R0kRZ4Nw"
    b"xOm7MEyckfW3NPLZUT5rRlcsLShmfdAkOtcKNkgQN4tiTF+Ddcikl3KziLSS3/iG3uRtZieV2V3m82heFp75zF4aboDubAEncW+n"
    b"LAYjofCHvVkxzoXcFJrZCQCGbWf/eIttj2d2pqx1yL9Y5W2GeXovVvEFxrcxptjc4DxbKCDPnMFqCo44mg/KyCkze6iQml3QHezv"
    b"T9COlk1p5+UmDyqqYuNkF4DKXH58mC1pPgtqqlWhq4yyKoH8dmCtHE33M4qT+SUWrq3jz1YOiy2PBZox2l2kVRb4ma0djI3gPQsb"
    b"G5gGkw7yClis5JxFQHwPLuKLb2Db7+/NMOXI7JMqSFiueI7MsCqsYinqpRXoQHAgql+A1yceg3Wcvfca86KAV019i2WrJlJyx4zR"
    b"2081hWzVIfElHXa/5ylPqWLs2LFZL/pjuQ5xZQc+ZtfuyoNFSk1rMbodVV7akJJ8ETugJxE51gVaG9llx7CINMjzMF7ns1RkIMeq"
    b"qoAKitlZ0Lmjk+FoVFzCg9lq+swFq62vjjLVRY99xYL0+MXZnQbcQYsjpDifBbodK+auNbNQfFQkPKZjIPphAUuIXz1O3KBv3crJ"
    b"M1kR19cW76aaE1R10GGJauX4CCxXjp+ZUIq4kiwqwhYu4Clp48uHT5NmAfmZyez963ZyIeltaslgMHIFlh2mNSRGpkciNyBJPO8j"
    b"8gRJQHS7cB31Z2CjoTCyUdAqco9TrgJvSsHmDLL0hvY85vz4v43Nl8y4ubfM1qqllqAf4rNYTKFC4jfzP22COEe15clD/LuMGgIG"
    b"Qm2+MHX5chRrRqq+D9W667z/ToTrHV1UdNt5byW4CfriDYVJppRP+qm8BeU646W3vXfFuHZLlfdkMB4dWQxGRQaDJiKqs/B/kXy9"
    b"mEXPwG5624ePfPH1gbiOWs5L1KUWZUzuIUny8ABs5rBSOCN3kW657cxQPe+xlxkm0rWZ/1A7OEanm75SkqZXk8WLlmi7UJA1dRe1"
    b"y+X2gLX+KO+wJQFeIxkckxEYUELqbV1aM0UVVbJZf7XgvRLDI2QPjF5LDzvAHrQ8qH7F9Ie6M5EPCw+isbqANg5rY6BDTaRAq8Kd"
    b"K6lRIpqVeTgYdVuPuO0hx3L7OlDDhMfpVfZ1FxVMC8omLFazAOUdalJqhiKh1irHvrDeojDP5z/PzmEk7BV4zjAM4fAVmk/nxJkv"
    b"bTakAR10rDZ1+P2GK/Ajf7MhFzbL+44YOshso7P8Vw33sJKb/xmVg3x6dP/eZtBYfZpL7wb376ZB8Adzj3eMG08UY2l8f3FEnFXs"
    b"PSPgCUxAzd5exzIBdpXHDDdDu88RfGIeWJgvU+Qd7aRgnisgSahWwXOM9BF2/eaPxurL7GwSg7uTdzI7o9nFCX6p3PMJa9x8sMDU"
    b"kV/fzKdvG/fuZ1Mr7IrhowaPeMDyZya2mBiy31T5NLrJMucOlT9COXLkiAnUbV6u8rtPSxy3YflIz6wainrB0F5RIz7Ji4TJzQ5g"
    b"0RvLhIg64Z1JgwCUKKNkABYBdghrFb/UrjV/0lgXqvcr7YOdwCybQ4G6jx0JNlMroKFS9WwcArtQ4K8FXgnD/KTh1J/J6zL3Bg8L"
    b"oA8dBvoq/3gss7VNWWZJGeA1t/1ICeuypEaVWmBgUjS/QEqqKyAlLRgzj4zkPKHr8K8MT5zZXci/eArKdGZ7EhOQBDDTXSO9hknV"
    b"6+vQLXqycNCjK6rDPbY9hWWtabaN+SfGdDJ7M20kZSzWJLuNEGS2AAML2xOa8txjQVJMwXsDLMjh6JFhWwpYoO+D1FQpZAs+BeNA"
    b"44MaSx9KFEQQXXx5Y/V6bmbMAudjVL6gsXvN2NrK3XiTHbmKBdF/2hBARfde5568QqIzZ8OcBMVIjxqph9nnO8V9Wt1mcSCx3eys"
    b"rTuiftnWf4EKZ2GNxISmN4dqjnaqylHFR/sS3t6hIydCdqA9+3SQ52lgUNMTujnB1lZv7iaYc62tzxFd72vwK+GQOy0wHsBjvEEs"
    b"PdupWU742lDIr9SGGjzha+pDdUGEdULOdXse9h0WY9ldyN1/tj/3Gnbfzfzenmq8mBSQYMlVnvDc8lXcwStruFP3vkOQ4PQas2N0"
    b"Ci9Nw+QjxezMW7v0APV/Ax29l3TN90EiYovnuV64lLAdP8oClWodxgM9WGhPsFNfXe3xhsaqoiEiVMS69Jl8T/+g5nkDDqW6mQyy"
    b"jqJBUnjTiWZmf8Wf0w775eLvONcSOdOAlRAxCJ+dQyRC6ANh5n2AyspFgYotADBGHy6Fk4J3yFhfWJFYIAqaWZudBVJzShXCz2ZG"
    b"g0ho3+NBI7KerZH9qyklSIsT/BS6OMEay/7IAh8iAllwM6xeujQiU4bsthc8DLj74rPs4jYwZ8HhCFkcuRo9FbrNp8eNmSnFhUia"
    b"ST/M7Oy8G7kN/7HwwQr/pHeAzoZVPub3UBBwHQ1QSbZnmK866sLZFwzWqS2RiIspUsW0XboYbUsQPikw+7oivN6G5+HaiKx0qUd1"
    b"MXdHdWKmEhA2escptrSK1sa+U3WZgZ7zBGTWA4n4INi+Wv8/TSA5e7mUNVjA3CsqmEWz7+LQEmt2pATYGLRH6pSdIzc3Ax8OlTff"
    b"vYmyPEG6iJFA74olrUhLWEpCWfh4BzrZcRT/Fnh3XXFN75Y1O3bPYA01/sM+F49TTVBwWHH+ZWQGBA5YooxziVJofYmhlH8ZuYUH"
    b"m3yCYCmehMln4vm+VppPKD67PklnzjYa3EphjLs1HNbzJbUf1SZ0Zt54gqEByTmBvpJayd7ZUKiJIL8X91FfoV/5OvQ9JQ88t3ML"
    b"lEdZu+PrmLCZWgH6zs49Fi1BeUFp7asPh2pDmInDz8aKarfXsUTb9Pr+0jJOABXiyd55a+xO22haxMB6IEviTz7vtajiarjiG/sJ"
    b"7RUWWM/oulSBX6qQglPEy6p2JxIxvSkYjLX1i587+oO64ArmCNkLW+cC+bT5pNhrhsCYVBmhy5n64RUeXNHUVAiyWVwgH5CQCQ/U"
    b"R0PkGh6iCAWYZs7jR7Eanb3e6OUqlrXzSypPNwOT6Vq85rMLbDye/Tx6/jPg8J914OhqTvYD56KMb0WFJQIdJnHZGXGnfql1aXEt"
    b"jvd4rZ9UB7rjon2aOcpQANn7bKZFh4Nxge4tEO5R0HdcdMr1TqRpPx2OuieLfcwiOM0LprckP/JE7SUnhGXxAn8SLAdjCdB4A7qc"
    b"eWRZm1xacXQFxfHttyBwWJPgmlgsduj0c4GtZGN6Gc00Yag6DE72HEmGqeAzpomdvfotMBW0ekJs+00ibiv9pLybSGLgE19P8mGP"
    b"leSToDy8YEf3YP9FihsAJpJ9mHQOwLH5i/G0BcGbQfXYHgsyMBV8gqt2PiavMhcLs3grYswm54Sqwkz2Zhou0mCZK46l8uuztuEh"
    b"+tneLJuH5J8pKGsYY5seBx0I9J79kRHJXp7MpJfy61fz46+MjVseqHROgWEZyC7BVmQLVUijV1SKaMYychjjrl8oFMDmoeanNrEY"
    b"ANnA7FmCecICOck7MNOEFlEYdU9c60gQjcu9slOnk2Ko6Z3gm3g5F2Onl2wDXtAbLSLp+SHFFbzDinurunboAtYCYmaAZX/Q1EyP"
    b"gt6KJ5BjKdBP0ZeE8MJh05VBui5i7tooyFl8bn80BVtOHNdw/3jsuLtg3ELXnMjnS69h7upWCjYaRSmlOFZauBvGXsFYScdPWU4G"
    b"zzxtmaWR0WNNoOTRknZS8URusXAOWx1NgqUfwJygQkmEFru6kNuZReH/0lk9gjiFRJXm7OI3IkWYB3RKgfHPCOOg8gjjY/KagHe+"
    b"dz+/8Y0zSomOeG9OGEtzlvOghDrEq16NipEYQG7nuSjmxMaJaQVlN7by6UUlfKo9qCvo9F1MOpMp4xrRGWL3kfe6qQIaJGinQ+7a"
    b"AZKBEdcugAoC8sdF5X7zkc3i3yKgX51lVtKzlaSEC/PTM62keEeeLEN4bMGe0iuwpYqAolhswUs5GD5gMLsYeQl3MQUiTOS2HzNb"
    b"xkOF2jpFyFMPBzEKbC3uAOXobbsg/PiUN9kT+wtckWnMyvVlZ+7CdTlf1S4MC9muEzZQCOiRkqE4o1RtqnQ5xLCGPTvjrNRynYUr"
    b"60xktpbprBYhrYfK9iquoQ0bTzAeFCl4zlwrKYsaRKojhVokSXPwB599i1JayAUmjdE3mb15PnKxzk5cjk0pqpc0zD+BitkZB6Jp"
    b"CQx2tLCNoFrLfxCwsVLBWmZ37+kbK3JiXvrUnBtiPgX+LjvJveInxaBpoG39l/ov910a1Cl0g1kghVtQ/IX1sQLTpZQucv5zXl/e"
    b"aG49RB2uaPHAPmhhgfnhVs9tTv4xFlA2Q/6XSycHJ1e+fGc5fISgp6JfnjTX8tculkdUStHVkiecFCtzakVGsBSeoZbHF5YfT49k"
    b"AeUzO43YO2z9oK7xUutjnTBXuDil+sK0P85sM3kqarYL1xyH6CyCVU+ub2EAqoHuRJ/wNfAAj1AiIgmdavN+/Nn8iJKIDribDjJg"
    b"98uj+ba17TpSd1o9LMLVsrLri6/dkku25kFaffE1HrVHkciqmQ6rZT+gI7xyEkGEJlK53RFjchuG71RYvb27XLldDDBS2+TmEKh/"
    b"2ZwRwtLmiumBuKjvUA1Ms9ajGBMpuNiHWQgiGqVKEJGaMAX/4XdcQLyFPXr4yT1QPeEwc4lFlTNwZdavJyRnVckicXFHJfjKmBnH"
    b"z/D6H8Qy9qJiggpvOsggzCgeecuCzqwNS0+K4fYrLLdt7epLVMoQ4cLUnByYHzeZAYQchQOb1dyqvdrfOqsx4q2aIt2q0XSplpmY"
    b"G1ECfYqD/RziRs+I1HtJk8IO8GCYnb2/9aLDCNxeELfIkibuRLNS18TJAtKEuWlbYY+9whuK2YEcTgEUb7nJBnxV5n3JMeCmTqov"
    b"TcE826FWv/gUtj7Vtv4WpOxWF/8/CNqM3zs4MVdAyCWJuBT5lhoxjDf7aja/PmYk1zCZhD0ZdLyLQKGHYL6iUd5yJBGj0b62nn5Y"
    b"MB6bjtUNzsV6Cp5vPRbo6cdFvmLG1CHaGS5cLCDDUBYOG2Nx9HerDHjLef7Z2Y0mlaulYRsLYVOchFvRDbYfC7MlelSgCxnYsfCN"
    b"o7iFF13c3dJPoGoM8GAVSx1/mNnezqRfZHbmM7vLaMiLtxK7MRawV2xVHS1gCBz3glVbqWH75agoYiSOoKy6g9BlhJPmpXcRt8Nj"
    b"Ep1aVxuWWZOqEBaqJFUROUox/aJhpOjdrRiuEZangAPApMmXRoQhdVzwGX8UnfPTmKbcQ+/q4UmSfpRNCfOhz57xqSj2S00ihXBB"
    b"hDH5yn7dKp7o/gnfMdLUGIKV/S9ghPYq"
)
_EMBED['hg'] = ('红果短剧1127.py',
    b"eNrsvft7E0fSMPq7/4r5lMO+UpBlSb7ixNnPgJPwLQEWnOzu8Xr1yNLY1iJLQiMbSF7ex0AAG2xsEu6YOwQ2AQyBcLEx/C8bjy4/"
    b"7fkTTl16ZrpnRrJJsu/3Pc85eYIlzXRXd1dXV1dVV1W/pzW/36yl8ulMbqRbGy8NN3fhk6b3tHg03tEcizXH27TVt4/+9fpy5d5y"
    b"+c7sz5MzlaVb5WsLicqNZ+btpwl4ad6ZrUxP/Tw5WzsxU1m4Xn54u3L2evncVOXy17Ujt1dfTpp3vv7n5Fn4f6JdM+fOl386XPlh"
    b"sXLkFTTzr9dTyUKmvTmXL44ls81GJjecz2UzOT0ZGd6Xy0/o2UgqP9ZC31oK2eRBvdgyNp4tZRITmbSeT4zl086Lidi/Xs+MfJkp"
    b"aEP59EH4Dg1oB5r3jhbzubzRcqB5VM9m6MuYnh43klrl4RtzfhYKTuhFI5PPJQATutbZ1toa/9fr6Z8nj5hL58yle6vLs+WLi1pr"
    b"a0e0M6aZDy9UTx7RjNGk1t7RnmzTh2LYjvnoMmDhX6+vVJ8fK788thFHee7Y6ss75as3K0tvqy8Wf548XF38rnz0GHwxX78yX53D"
    b"L1PHzYe38dXkYe6OeeVabXLSPHa/dvQ+Iu/hhfLC9+bJ+9idR0fNue/Ml98BanEmVs7Ubv6kQbcK1INjC9BfmIfyjzfLC9M8YTBz"
    b"5qNr5Z9OwVRAT8y573EosahWufdN7dbX5pmTlekTgIHVlzhGnLvpE9ASwqPZ+r766E756X3z+Ez17QnoTvnRT+ULz2sXnkEXqo/e"
    b"mHewsjl1mcvAw/L5x+bci1Vo9so1oCJo6B9LqyvfAmLKP76tnL2vjY4k0vpEJqVH/m7kc1p55vDqq2PmzHmGZs4+NecWuQc9v+F/"
    b"AI4J9/+5fvZu5fpDc/pepHBQY7q0qT3WoZUvXdZsWjenflhdWhI0fvlrAYJ/Y3WmZkB503vQAFMLYHxTe7xTq5x6DQvEXLgPg4a6"
    b"5vyU+eo5kchUa2s01topKAnwB7QUb+/Quto6023x4fQ/J7+Dh7XvzsPswmRTP5hKoE+HcWroP3MeZm0SqATGwtCRXF7fMGdvImE9"
    b"vG0evmxR3kzlwYMd8Ehj6gRITODlhQfl8ydWl5/DTAON8XiYHPAnNdtiUe0RGiWt6e8B3urL6fL5VzAiAGIuvhIrmxhA9acXqysL"
    b"PPDVlwvVu2+R8BamkYBuvAAMlX96Ubt4FkEtnUVoTPl3nq2+PGken63evAsl4Tk0Zy1WQFt18UX5yRFz7kj53GMYIS5y+BjNGyX4"
    b"UJYwrx5YB+bcRTHQHy9VHj3hpQDtExIZgRpwEq16dKZ29Qb8hUFVVx5ZdFFZWuSeIiW3RO0Zu2KevAFdtTtHr2Obou1d/xXbFGu3"
    b"CoqFBLzhaO3mEkxl+ewrJCOZd00AR5k9V7tynHkiribqJDCdytfPCbC1gmaqL64z7ZUv3DCPPYV+WOChPwjYPH29cnY5GI91REMt"
    b"1W+vmsemg7G2tmhIQ0Z08zbAwMkCeoHphvUJrKOlrSva0t4WbemMwxCiXVENpoSLrr4CaMCDZmGo1uzbK6UTVwrO5My0RvRe/e4w"
    b"zE755EnoQfXZfaa8yo1Zcwoma4bpLogNhLSNGnPHILQdAlpkLikYNkze89WVS1rth4tYA7oVainfOGGeOB6EbsL3a4drk9eD0HUc"
    b"1TR0tfr2Gkxl+eIN8zFQ2yQQnzl1o3yaGPjD20AsvDpwUYj1yovIZsLVe7fNxeO1b99Aj2WWixN95zKupGmxCdBb3NOgv36rykKT"
    b"va4qV17i2iDOALO/unTcvAJAv7Zo8J9nbmjyXqaZt67BZGqjmb16MaHsU+X7N83Xc7AOmCRhmmDBAC6dFTLj7Gxn71t8IjGi5yxA"
    b"sDTNly8rjy5A2crSd1qsa8zAr7BfT82bd55Un93FvWfmPPy0aR8WkEVp/zxzU+ltopgvJUsgPIguIpUvzcE4oT6gRxnEP49/w6Oi"
    b"b0bmwEg+TXxoxuopzFH10ePVlbnywmT17Rns0snrLEVU7mHByg+XYIkAg6i8Xa6uPICNCIgThlpenCs/uFk7ulK5tFKeuY/k9OCm"
    b"ve+Int/SeIepLv2wurxibzuu/Qj3SyIS8+2x2s1lBG7tftKON1W7DJ1cAirht7DjQXlYUVaj09KwaidmzflFc/40b4DMdcy5x8xm"
    b"8e3rSd41nc7e1szjL7DWyfswSvPYFLfDFcVOeXzWYtdrdkfwFBiENJmIceDKZwXnrr69xPu7xfx4A2qBTaDyZLlF7AXl+YXKs1ti"
    b"S2gBoi9femwufQercHVltoUXvXlmBbm54ME0ZqL/f8OuPlzMj2mJxPB4abyoJxJaZqyQL5a0ZC5HhJnPGU3i0VDS0Dva7F+ZXNJI"
    b"ZTLWb5QanXeGnipZv0aTxmg2M2T/HEumrO9IL9b3vN1Q9suxpPW9mMyl82P2L936ZpSK404TJX2sMJzJ2m9T+VxqvFjUc6UID8yG"
    b"XRot6kkU1u0HmTGdkZDKZ7PQbRxyJDmUsjDxWbJQwPJUZrRUKkQMvQh7pfV+M6Dl0/7+Xbv1feO6UfoUOpzVi2Gt32oJX+6hKgyj"
    b"dBDhWdV7cwf58XgxC1iKFJJFQ7de0o/EPiOs7RvPl/QwFtJzuEHTV3rt4IbaN5pKxYPdTUibPKriwUIpP1JMFkYPRkaTgNpSpFDM"
    b"jGVKmQnd0KQ5AiSts1YklSmMgrRg1d5CP8NaMjuSL2ZKo2PQYeRuRpN+IKUXSto2KtdXLOaL3DVuT+vRduRzOj1hGPDEAQI/CIpV"
    b"TB3YFupiRNSzsNm3R0sa4h38qNsBu4Q/cKT1iFEAPm2D3sO/AHoCp5x/WvD76ANIh2HYwPA/i2IPGlQZPu1X+ANmvDQaASLTc+lg"
    b"IBIJhOzX79YVrOHfHfwvlU0aSnnnFf5XgLdNwFs+zudGPsu09H+xOX9AQ4Foy2gSaA8k9crpRfPWUdzWgTG+/E4hEeSPdy6jnADy"
    b"OghG8LpwkAvA6tWZbVWWryP3PXbXnEPZqHb4rXlstvr4KAq5R15Vrjwrn767+uZq9afz5evzLL2aS99i3cywRR4ZQwO+RDPG/YcZ"
    b"TGzu3fKHvh1bYSYDcqcCTaCsDkszvVZluctY2fAvloP6gaYmgdBdwF2gQCzexYUDgQDs+9qug6VR0M3gTTO8wo3qzRWQORW0tMi9"
    b"RWQD9lZXkNvDoAFOEwFMIIkG7cnatCkci7eFYzH8bA3H2+LhWLQTfsfCsU2d4bauMHyJtobb4F17Wzgeaw/HOuFRrCsMkmc41hqF"
    b"T/gdb4f30XDXpjC8jbdFw3YLsU6oGoOiHfCvE6q3d8B3bBL+bYJnXQi6NRxr6wy3doWhkQ7sRyfAbQu3Yz0AHd8Ej7BZhNURboOf"
    b"MacJBLQp3AqwN0FZ+AU9wYbawjASGEEcOhvvCMehRCuMsxMexTrD8K01Fm6DQcErHHI0vCkKzcEo4uF2bKFNHsWmMHQgDgWha7HW"
    b"eBi7Hd0UhvG3QsfjMAYcH4BFhAFEQBooIOH2znAn9KMj3IUYw1HBJ/UCarbHwh2dTiNQG57EWlvDHThe+Ad97wx3RcPQqRh0KdbR"
    b"Fe6CEoAhxGAbYg2wCW0AUuNtMGZoJQbdj8OwAQygKt6OKGl1GonHcMqgKACHFlo7wpsQV9AT7Bg8w+mBIQJWOnAogBWcIMBPexjf"
    b"wVQALuLxaLi1LYzkAhiMAZROac7jrdgNwCw0FY+HN+FsQ5+wGswpIAVeR8NAGB1hbB97grQFzXVCaXiJQ8Hxx3H2oCpMFCheYRiL"
    b"MyOA/BhOCdAEziigDJSZcBciAoBB52JEmDgrbWHsD3Yeeg0zCGWwBjwA3MY24cABZ3EkMOiRRFlIr11IKPgPySYeRjLGOQDqh84i"
    b"qQKYtjAsFiDiLiQ4qIOtI9qgWjsSH84BVCcSgart8nTAA0IjvgcChQ4BncZbkbyAatrDbYhEnGkkTiQPpD8Aj2gByoDWYaF04BzC"
    b"MsUPaAMqysQL3YrH6SfvBondW3buQD4QPQBYhT8x/BPHP234pwv+xPBFHP+04Z8u/BPbDH9aO0LMStL6MIh6mVymlEgEDT07HNb2"
    b"6ge7taGDJd0ISTvWsAZiRhDehbT/0aPFOtS9opgE+U77Ipkd12lHDQYEm9PyuexBaf/CJiKJ4l7oOH/VDxRAPCLAUo/E0wYdMmwI"
    b"e+xn++FZNmOUGJq9ZeZhk9AyORQcR/RgW1hrawup3S9Fw1opBv/i8K8VoOwfaG4bDONHK3/E+SM2qNQDrGS0DVobyN9aVAXpC9YY"
    b"KMUAEHzE+aOVP6KDPnW1v1kjxJkeyGgtLVqbWhAFASSBjNastYW097U25fX+iH6ghDJEcP8AFh3U/kZ94l+g5cboSUx6EqcncelJ"
    b"Kz1pDTkILeogP+e0/Txf/9NApSA1psPulnZm8ABK0cFkNyC+FNKaP8LPbjeIYDCpffihFgtBE0iZIe138Pnxx4hYeIU/0LSB+65U"
    b"lstI5ALyL26biaFsPrVXEA19t8gG26dvKv0QrVBBaXAOaRb31qOhWIeLgIyBzCDOV3EvfFFqFXNpqV4YWJ67KrQ3ICh5YGiQKg1h"
    b"FWPQp9xAlCimnf7G+EeMf7XR3038iH8AeXkICx53cRkmPqbETn7EP5hGO/h7bFDtB/YvJS2nkJfuM9DVlIca8b8kTExYSwENpmk5"
    b"ZKiNDJGi9S1uf2v1WRaoDgC1DMG/FCwRLe0pMo5FvC3j9JSgAqNakCdCCnnKDvmV5Ra9hVNRv9LcN2/ptF9heKiNe8uujR4cqYNR"
    b"BUB+eBjeIvW9D9zaM4ONiNlF0AhpoyaR9Xoo9jeh1l9Bqe+wYEFaVMcnmBMxjKAh8Zm0/u58BuuNjWeDOE+uPhQAR1HPzCScXnf5"
    b"ra1hwPXvtJj3DYP8mx/xj2Zo2TA/9VkaPZqLufo1O5rxb5NWFnJvn3X00UcgK6iSAiO30PTv58SeifXw401hDRZOc8yXJQviFcQn"
    b"qLdTIt6YTLxAfQ14bbtEwGIBCAreJFFw6+Bg3a1hW6O94d+42P/3s3zqXY+1iECy7UNxAX8O0c/N1k9sA35vtX6n6ecmX8bKwo8M"
    b"dZMKtc8FdbMKdWs9qHEV6lYV6iYX1D4V6uZ6UFtVqJtVqFtdUDepUPtCTb8tZf9yql4XRf8yYcvDtZuaJEsMtgdtl8YLWT341QSI"
    b"pdxMWJvAlvTc+JheTJb0oFondAjbcnUo3t4RQvgk5xbQRp4qFRNicwg62gpQfX48V9KL9u90spSss1cAg0VLFJXwjCkQaJKUMAE1"
    b"pH2o6GHiMS5E/hbJ/n0c2CqowwDhr1GhhTlGLN9KA92xDkZqksysEj4ctQrGC68yaEsv5scSjHMBIKwFhjIjorH8OAps+D5ZLCYP"
    b"Bvkp4hMYjaGXHKQC5eLYcPwhkJLlOd+L/YDeRFQ5HzoRKeVF4zhIbtchdu4llsPVjltbMBijbS7eBeiHR07R0fEcbjfY/AB3rVv0"
    b"EKp2OFQGA7KUqhQssr3MG0FHxZF8mSkECRL8NkRHFLKE2i7CGUr5Ek5m4jemGcIrqKoyweAza8zdUqlmLahWCa1JEIWiPkGK6ATR"
    b"j9VqZiKkoQTQwSoc/PSnyfpkklkXhRBBWEPJdGdckwYYFhSkSnAugUOaW5TIC9QBYKEFa26hdpiGKhGZGDmBajzh0P5/I6NQLNRu"
    b"M7gsnvILXClsUA86py0RAEJzLM5uIlv6d9vcJxSx6wY9tgH7VWS8kEa2ysS0UXoxnMkls5kvdVHZp8uK8V1iWdaxkG3Gj+T0/UFl"
    b"i4BOh6X3n+3c2peAzocBdbmU3gN4gjWWy5QyyWxiAq1WPWJYNhTPkLhZa9A8IHnCfXcCe2Z5SlVa+O9Y+/8eMti8BZf2/zYKEE2o"
    b"8+875Zu3hInrrDVr6lRgHWfC9mzr78NDHjzoNbpbWkbzuZGR8Xx6PJn7+zh6Ugaa+nZt24Pt7drd9/G2P1PhkWa9kDEAXc0Tse6A"
    b"7SlXXpyrXTlevXe8dusM+p5cO1WembZP/Ktvz5pXruG52dWblVMPKj+c4sN/dG/z8SqyXSLQV+PqTTxjG0tmconxYhYQPZRM7R0v"
    b"0A9zbkbbsnWHtvryNIM1T94wF4+Xr86Xz1/6efJI9e2l2omZ8smTdk9WVxZWXy4BaD72gy5xT8qXn9UWfkQfnuPHzMeHa9eftsBg"
    b"qiv3zYX77PGjJYr6fiAcPTGWz09o6Glx5x+Vr58L58u3VyvnsMmmxKefJP74ee/2bf1/SWzftqPPOdMKBnBwsEID7AIUCIXF8zZ6"
    b"rAXY0wmfh5oUIIkdvZ/1Jfp3Jv4I0L7i0zcBpFuzwYrq8IQB8gupQBv/pLdNh6xFaxSymVJCTGuilN8LuxH97UbfA1qgJF8OwK8w"
    b"Phq0z/8Atdp/qDTx4b6Puj+cyKQ/+g8NEFe+Ng/41oL2BITRoS2EiD722nz0qnzhXvnGa/P1nAcMgRCng7QX5tMHUdEqFblzGizq"
    b"QMBeYvg6YpSSxZKxH1Z3UCVdeU9lOPgxgPuuu+CgBTHQHcANEgs6tUf1JOycpWQmK2BECHtBKByWBS+0K0DRSMZIZ0bgvUvUF6vU"
    b"gSavXWu6EDweVJuPLlZWzrAzjbZnz27NvLKEHsTokxXVYIGsvjxrnrix+ur06svZ6qM7WiE5ogOG0ZfmzmXz2NPa2UfVxdnqyqPy"
    b"7C3z0bXK6cf/nFyovF2u3fzpn5NXmxK92xKf9e74X58n/tD3lz/t3L0VSXaAp7h3W/n1D+b0PaSe3m3myfuVs8v8nf1i7edQjEiQ"
    b"Svduw++rSzPlBzfNY0f5J4ES1RmQBaJpsAnH2Qz/kTPcwhIvucrrb82HF2HJV0+ghx3QUGX+OBWjVbald8unfYmt23Zbjg3Ow896"
    b"/5z4eNt2WnxdDtrR124ScMKrFRhW+dxjV63Nf+mnWm3RKBodovE26wNrTy4DzdZOzCHuocRnm121ez9BltoBVYCvRUWbsFCrb0/A"
    b"U/PxHLANHow5dcNaf6MjiVQyNaon0hnYcHC5AZEzvYxk80PJrKaM1qJPFQXJXFrLCw8LJLpiUHkf8uwyXpgpgJHBPY20WV4H72mr"
    b"ry+ax6a03kIB2O2iefwSz0rlyiNz5Rww8J1/MFeeAK/UWoRHhWa+fFm9dxh9u958DazclnmL+TwpRo5IE2jBzahl3NCLLdEW2HIi"
    b"wwBiLBOBnhTzmXQkv7c00ULICYTdtejPO9ap39K7t+Nbw0inksV0Sy+Xedc+rrN2o7pb8/tz2XwyLd5J8+5Mr+WCY9HL3/OZXBBn"
    b"J4wbfCIF+ihTpKV1Kk4+a8CxHNQiI3oJvxNR1wNc34mHvHTetW34Aa2m9qd/VYtIqwgTadVp0Cmo9IgULCMyltyrw0iNIFYMQysZ"
    b"o5TI7+3pL47rqvELQKFSqPSbKwUi+wNqWdzJtHwB92OoBSX2DwVC6Aw1POo1VQ6PRkg+CQ4FYi440FhRH8tP6ARHfefmpNgXX8u2"
    b"/Lw+Ftn4kitlcuPs7eaGb9PH2N40fg+CpjmcOdBjT1dAFWQVNuXmmNipIEgKJKmg6yAI3qWDjtxiM1IjOYwnykU9YowPBYuBgb9F"
    b"mzf1Nv/fyeYvE82DuCUFSLRBYKHQQHebOLreV6eSXEW0SgLJvgDW7hqUh6BMtYvbA5QNRmIDEFChLaBt0ILYURiIY4izy9NZAo0K"
    b"v/GwiKX2uLcQpmLAscTIFaLN5dGlAM/oInRQpzoV5JJjOtI+9BtbQpDYjkuEEYoaFo7AQmSpK0Dj8LGjKyRhN1ZwLwRmQggz5NeY"
    b"s8Hh6ILDhfW25FmyRBNiHeJBP8JSCjSm8PpDQqxbvOmrAPYWJO7hAsyzASphAEkTGkzgD3g2hui3H9IveAriGzzDSWqW3xxai4MJ"
    b"ehMzzl0x8kXS/XqyybGhdFI70K0dGBDtDoZIqLlwD4mqfP6xTLRU20ODqayezI0XgkAmKR00+Hwe5eCPk1lDJ8p0HA5ROQANkMK/"
    b"MIbj3GMQm+DL6sq3lXuLskDHEh9LFZK8r0yZRczu1dDkIhAuh7IQ/aJe+jCzJkcgjIU0EM7KC9dBIKtduiPhElVOZ/3YhjvgWbg4"
    b"qCXPisC3AzR/g9pHmlc2FAAGmBgGtQ/9/Wv8qFXl4wyFyGvQe7iyNvEqG55dTTGhq5iwaBobDkn4i4dQvoW5ZfyBfA305GyV+VIS"
    b"KcQYHwsesEeNeDxABlAC7YDbPwpYtVCPs0gGW1HKg1AW8AEWt+J+TZK8i0Hks2li6DSiQr4QdDk++GLewTpU90f62gj3IJs73dyj"
    b"EVDGjITX1pAmlsejU6CraKWxgkOb9bn+u/NwF/+GdkDEsCCgsQqkkl9EovUY+68m1zVEODfTSoMcFiQtHiMQ2N4IfMthUxfuYSjq"
    b"uWcYV0dcCPSc6tEVjH0dmkjFMWRm+Yz5ZK68MG3efszGKXN+3jyxZJ5eXn11ypyeBQ2p9v0MeXKfYrtR5fX5yo3D9fiZYFeqbUHi"
    b"vsRRm+RDaLa7Y4UQGhjTIOUZJSMdUFhgRvvQzU8EQJRD/Y8UCSQfHHdoeH64UYtHB5F2Elv7tuzc2rt5e1+ib0f/7m19e9a3/1Bb"
    b"7p0D5PJGghr1RftPaQPxbjq8zfC5DIrnPT6CoA065It0lwCB30OK6gzdxKUo3nykdbSp6ARtfnEZbX9TL2DD1GgftT38MbT5m4fm"
    b"3FT11g/myrf2vrIuFjNOkhhrAoiFX81gHOVBqBfFBsqDteuPRjCUJ7hOScMOaZF/e2T08Xoz7z0IcKZfOgdAbuQc3H2ozIm0n/8i"
    b"mmhIZVR6rCCUIlgYzB6bfNSzsUID7czWzBwzvc0qC9lkSuf6RHPr61n9mfGQl0T1pJWyimoPJtRov1NLrlP7E0zYPg/KGInhpKW6"
    b"OJxXkIx8NIK2IfUkJ+w6Kwn92wHjaQgyK3H+Pl7MClJFW61eNLq1dCZVEpxKGB7DpErlx0vkFYwGwKj7WAspEysGBRik6a+EQF8k"
    b"kYRD2pABYaN2ez2jNvQe8SlqRcg5PQG7fQI1mHEjqCjOxQgqKHquZB/MF/NDQEz8MAELagSWxy8bX2tUdX1uNDqFIJWhYuG1xoqR"
    b"dtn8/kQRrSt6qmS4LCpA3cUID5+j+T9Eu6zLHIESaDEiGiEMB7YwGpq3ExpY4nEVEZhqzooi7lUFYHHnQAtAKhuqZ+mXZgTQhSV/"
    b"keFr1EFxSHo4ENiNPgQBdKMKELn1RJujAX98e0mrHm0R1or1scaNNkJa0SkRCEhiLe/z0MeWWLy1rV2ex0ALnbekXOF6lgqRKlpH"
    b"LS2BEEYswLQXM4WgZ16owjqng8pKY14npQQkFEOLHhIgwhDTDUJEzFcke0dyELWi1nJOC0Nvgr1InIVMh2C0UsMaCPbim9/yVte1"
    b"dNBHNWiqBtde4H5EuCHdvCHN9izsDXWES2eBYyf0YlEOiEWFJUnGYslxqjXUYFP7ZSyzLtPIiYMJjOMC6dfPl5QjgXaP5xCiiAWi"
    b"jlKgtLbBwNEqUNU2hVOSw5V9zFuq00OjlhFVBxlRpES4uJOgFYF7BFt370Z5BaZDbVaaJPi7tvhKlkQjq+ugUEfi7dr7WtCaT/RQ"
    b"+8WibH2kbzCaN4CglQQpHiicsS/RWtgegmNI5VRQ1rL5hTvfJgwzyhf3Unl+1Obe60Hjw3PXqeOV6ROYpuLmDGqFKysUOoxpM8yp"
    b"S5y4CZROkVFn9lxl6W3l/ilJYbSWWoOtVbDGulu7PTZnQYyBMt4atX+LuXlPM+98j8eTU+fLC99Xrt+tnXtrLn2HqbwoWBk6CmNo"
    b"kjks2a4c68uHWlw9L/UeOHpFK5/+2QvW6hej8c496J0W+6/4Z5spHQniCm2Kl+bNqedUVMwK+hMnDwTjYQ1HijzWegFdbQuFtQ4x"
    b"ZMs1EkvH1K5z3bj7IQ+0pcVqyvKERIKULO1EhXYIBJu0+NmHDMLBDFAq9gBPzdgapMUE/4Z1wx1U3Dm5KcsUJ/NWyRVaNI+wYfE1"
    b"Cd2oWBIELjN3dCY55BU2SK/xJpaIcJ6HXSBp9x3QU+PoHwXYSwh09FhoQZZSsMVxWwkaLxm2X4Gy2qEoHrCMwc7p2tUo9QNgBMbo"
    b"JRWvHQn3ESxrbyKqQux1/oc+kcjhHWoSefgY7IUlPR3ErvuFF4Qtrg4FQGUygMEEQz7cDHA/QMi2OXF9HviexixDcApiE7/FShoa"
    b"H67jiqpiTJI8MnpKJ923KDZZQ5G7+X3GkJT2X9dP20NnfNjyV6U2QrLDL7wMWQsJVmY0sqldRl754unyxTeYkezRDDCtpl/fI9VY"
    b"Bq2TB349fxnHW4Z9YhwvGdsbRrjJSP4vUPjKilK4fOGucKhBMJOHnR9QzfaZEflx0EGofP4Veq49elV5smxeO7X68jSn4vnX6ylz"
    b"7jwet1AZzePkR8kYqChm4Dr7BM9nni5TuqHT7PQxP1Nemoe/2rat/3o9zal0yNK+c0d/347+RP9fdvU5GIANWk9mm9PF5FgSu1xZ"
    b"uL66tMTDctZ+MEDDIde5ADBlqJUfS+ZSOlWZelI+eowfF/RiJp+mwq+erS7f5qfQbx3dAPF5bfJ49dZDy5eOgWf1EaAewvrrG+bd"
    b"E1xrpJjfDxI8ondqHjY4fjqcHMtkySBgPnpuLj0ULWSTOfGsfGFOhQ6cT2/em0kb5Mo3P2M+usqVjHEDGLNBgygfeVA5f4afl0aL"
    b"mWxWL9LzoyfLRy7z89E8ijT09PB8efK82owxDoPPgThZTGapK28vlCe/txBglMbHqCFz7k719jFrLLlS0qDBVE5/bb5a5sf787k0"
    b"tw644KdSO+PFIR5r7eiK+fIIVzkI9E+oql39pnzxroP2NKPq/AJOKY86lWkezlCb9854oKczBkhi3Hrl8Jva5TdcK0nph5qT6Qlg"
    b"u8ByBXmvriyYx7+pXfqH6HmS0TN1cXVpWgU8kSxm9BKPdfl1dXqJa9iEB/1jKqI6g7avJQwik3Lo016wjYgzBTSN6YBowr8+U352"
    b"rSG+6/SBYScL+VQye7AgyGThh9WX58VgYeGURg82OxRZffJ97cL99UyizyRgWwp2Lby6EJLMONjo3fb/cWQQdTgcGlGhYgCLDhL/"
    b"273zc3YV/GpvtzZBW+leEXYV5LBYVmwpTpCiXz1cM3SIIPVu39a7x3HsTWaz6KWr8tEs+iCVvM9H856HDGUsmdW9xYd1/+di6/GF"
    b"lMwkGC3dmkIs8HwMtxH3c9tnVHlu9UpU8F+G7hfopGydJhSBJemJ/HCwlEkLaaxkOQRn0sIdWDEKoapi4Z1ny6OUlNy+RjQXJO2g"
    b"v5WEjJB8rlHSR/LFgwl0tA1Sv8IaPAyT523I0QJ5X6bdtXbzJ9CmWqyqLV9RtUMtX+GB+qHfY8WeHZhy89zj8uwjc+G+xl3endja"
    b"298rqYVUT5xz2CihL8rRWMBpKgB6ABWwkAJvZAMT2vh7yPy2kU1ZSSH6GLphyIaWPfAbmHbQeRspFcdRz85NWG4gzivLiibiJL4K"
    b"fG7oxeZe2JmRYj/vBfTu1of1Iqzjbo2CETZiJySjOIHBqRBv+RwL5NHkmNGDzjUj7DtDaggmoUB1D58iMcRCodAhR6aLtwtrVWmM"
    b"jXwlEDEl8+SYcPQC8Tg1GiwGgr/v3p/JgTry10jo9/JU/NV4vwf+AdEiqJB8WDUmkRdZLj5laWtXdnwkkxP2C5scOPMyS10868KK"
    b"M4HsoocyBkb+156dO7bqaE4qBkORYnI/xnPAryA2PjCGJ/fBULfwRsCTqmBwgu2WqEXpxa2gcbDN8qtDIWGitaj3/7JfNKkR7F+0"
    b"J3Zt7/0LDPjz3dvlEJHfMv12QG6mlzKa5ccihdG8nsscoFPIls7WTa1xLbg9kxs/8IH2+QeacIzVYvEPtC9HE1t2JN77NJkzPtB2"
    b"fdLf3LsjFv1A2zyeyaZbvmiLdW7b/UGp1Jzf29IaicUjsdZIPBoKwOC2be3bub6BDb3LwCZiLQEHOPCR/noNZIffGS5GAXDizcWT"
    b"5fMPQT0AaRDTj95+itmz56+VT09rDELYqzV0TJg/jdL96yPmy5dofJr73nz9itKC3q1NXsZ0pXPzlTtLItZmenJ1+S6I+qgsvHhS"
    b"PnmSWywvzmGqz4d3q/Mr5tTj8vQp9M8HUXHuPPwE+Jj79fwJO4lt7cQMsrHzr1bfvDUfXV5doTy3ia3bej9JbN+JDjo7tm6DhSQF"
    b"xtjOyxxLxHtRQjRPQ42UDpSsLaTFKOWLsMhbdEAW0HK6JbpmxZDUge07t/wBvR+tpJWR7RgzKZfY1dv/aTd5WWLIyyCbdoTVPZMc"
    b"4YNly79UcVpAt3wVjEcDVV4PCDdTira1XI3Z98KLrwb2cD4cg0UtOVTCM/S3Cdpw+egiEqh3PMxhAzYo2zEimUoBI3ZehPHhnxI7"
    b"/+BjE1GHZ1mqnC7UO4yxS/wSF2PVVRDEJ9QN3a6l9fzSG5OOdB7vOzKrNU+coPXiHRwpHAoLjgHCgcQd/xjVsdJam8wNUEO/8Nw8"
    b"fqn69gowBO69+c0ML9XVlye9i7SeX1KhiFtoYICRwo0MapZgIHq1fk96yyVDWjXyfolPfF05lD4hJ0ZWusHQNhh/zZGlnw8cSsVh"
    b"cpoJbPhL84ax5g1pbcOn3Rs+696wByV+q7eqWVPlA92NPWZQNKUktMAmegJ05QV7eIxS6lsv+fNz4e2BHV8Xqnj7+yz/ZSabTba0"
    b"R6L2nudseCE0xmT1P+lDf8iUWtpbOyOtHVrwD5/2f7Y9DCjaq2uf6Km9+ZC2ZbSICTdj8Q6Asyc5DGqyKB5o6t21q+5eG2uts9d2"
    b"iL32Ay3eHm1v3d3f1rnF2mc374r3RuBxRxR63RqL9LZ+oG0pAq2WWvr7d+ilLzjRfne0raO9s3NTO6eEj8aa463aH8czKet9qqNT"
    b"39TV2obv25ujm5qjXbBXf9YHk9Www4EmssYhFhIf9/Vv+TTR29/f99muftxcWtU36Ayy8+OPE3v6QAcjm10s0g5Fdvfu+KTPv7b8"
    b"yls9GumycqP6CHryqZVglOwZQ6scpc8gRWg7Xol2sIJ9fFfkIm7dhkEMZ4pGKfg+lTB8oOCewtVhPxGlFGdBEHSMEhrduBXQkXHL"
    b"C/MZcMgTsYjmbVzMcruST1DWF6RIKb0GMM86otosro4Xs7J271sis0YJo5hao4R97rB2c1Yo8hrFnDDldRdMxNYoihJeIplOF9fE"
    b"SJYc5N3F5Oky9Hpz4tCm6mdDBXwN/fxKiWENCCpFLSYB7wv5nAG6svjS7SiVu8UjIl4gYmsJ8NN6Tk7vabCvlV++FBv2acy0bB5+"
    b"bs6d0TAJOV0ms9G+TmZKdeLo1qwQcwbFZ5wa5fQHuQ7kZBCqyyevaI72RcsY5VraXOnyolN4ynBiqXzjlXnlBl64QcHmeJJ76kHl"
    b"yKvyxdMo+Hq2MxF/bA9Q9geov09YUctOBgSv/3BdnVOZsoAXcRyeD8gyv501l84CvgiHGwzAEm63QFPJEjAjq88YzOL4OaD55veS"
    b"oOTn9mWTCY+ZES0P2UmxSg4JB1LrUaXFSKjTfCcRzRhs0ZROHKAIIiTrRzGBx2+kODtyFZ2IkhcAkJ5wdhlLllKjv4U5AOGsZxy1"
    b"mz/Vrt6qaw9QUCn46noNBNgFNhJolpVAYNxV+11xz32We8vR/nxuKU+BhBHv/oD4D/2y9jhvQO3speriohozSLAtrw8dhE9krhS5"
    b"0m1tSM6c+2697n0J69bn/s5bf6bv917l9U4JXxbvvJYgh+z0Dcm0ztle1jdGK90U2jkw3ZUNXH4RCNWZOLmQ3/7ugi78C1S8Ok1y"
    b"55Mor8sVXS9DymRafi579YP1BhzWqK4rvsCaYkQxVLb3Oqc7if26nh/Hl1a8MG18okIDBZzBUSuUO2xUPxC063k8pxtwu7U43sPq"
    b"ygO8f+ibu8zxzNnD5rGHqPlNPXevunUnuF6rKfYGUpaaNKkAu0nJkFPMTOjKLNFkiEms9zox1NHmP19JDFbF105BxSUACqBLQOt6"
    b"2IggKXR3ApXfMrh2YapOC1Kzhp8DUcwPjV9i1pf4IOb5aeu02oZqlg9UDF7Az49sKBLDdgGPydW11nfqNc8DG/SsvpOEL3t2UJ+1"
    b"btGnQatYWJsYwmwY7WEt3tbhJCLLpfUDjtflhJybFXOAZfLjeAYwkSSVgQr/DkBT3rOJIUWfsF6qFDaRpOrQywEqMdhABqUe+paV"
    b"H6LdsDkeA1wOkYsXPAtFKB9VECPfYdhBu+d/U2qGlDywfiKKdddPZDwHSxh0moNB9vxgMLHu1tZBSruEW2yAiroyCwSdxR12wLEa"
    b"+A77q02otAA5o1H5wo3yuSmveIPxYImh/IEgh9OM6WP54sGJjL4/DFM8Xkyl7MRbjm+w29sX/gx216MKPF5pE7VDYSWlXpuaTJ8z"
    b"1VHtbgEFlswgsh7RlaaGMdQYfMWHeuOpEkxCATbMYOAjTCAjgYZmLfCDoQEpyzw6YxME4HTCCZu7EIvjWrU77kq86d/oH9VGNzqN"
    b"EkBPy8QOCBZ8tiei0Sj+k7qB3d5ol6jTGds7XNQIUwWZwTbHwugGTlMPs55ALeCdp94pqRiwOTlk2EKJSloWTIsSFK7vZJiEMXYB"
    b"puwfCItSJ4onHyHTJAYimT35/qdSEVHPUng+P6EMSKxZKJAQmSzJs71JomQy2SMlh7U1v9pU7zbgy02o8ZTuqDejNJRNWBhLKOjC"
    b"3mMqSCwCZKTABPTY+5cEYq22jC9pG7Qm3GnB+JISUdiAxPFsKZWvUyGV96uQyne0+VbAF/4tGKl6XUr5Vkhm6owBXtSpkK9XwXcM"
    b"gNFk7qCwmgnXRNUQFkR8hanvYeoQ/c2H6HAkKHnRAvYsALiCCTvigTuzjnuukoah08VtMGXSTUwiXAiQJj1UKiB+PBUQB+4KsGSS"
    b"41lOI1GHXWLrA23dXQ6bMpLo0JqgnbJRpa5umblhE4ZyL9OA3Pqg9r4CWNkMpHLKru/yAq7bE+DaGwUnfJ+4b6xDfqBy4Dp7l9w5"
    b"R3QdlG6cIUfrRCk5lGVc4swP2xRgTwZ1HMlAnjK5rnuS+F0jdEu11aniF/szaTo/aavfny6Ja6vu1a4sxuq2K7XrsSN2SSiW+9FN"
    b"b4L2BhhS36uu1qrdkTIYh31ykPrMl4Q1LjcolFYQ19ai3ZSKRayT0VW0BNdDeakBGQlAhd2aQopifYTXB8tV1U3GHmAN0SPhQUYP"
    b"Y41pnQYcHbSnx1mXNrywFiRNPCHSOouKiYJe5EchNXu4wGTIHbogntsSUmwQGwYlx1EI4CHsbCjsWEDESnL1zT4Gp7AHe7xSNzk8"
    b"AqMlKMJHJhSXDKVgY4B+odbgGaW9KyWGs8kRw5v7G9+B0I8J46Xs31QjNV40KK8szCguTweKrR+1yVoqFkA1Va68UWuvv4tY3DM5"
    b"fsDm89gdCYDIXw0FGi4MVy2akm53R5xlYzVYh+tbr5HA7Kb92L5VsBHrx+Nmn/61W+vDlWfFZ0HYXfDE+NUBKaiR5sN3PxATZqOB"
    b"DCd2Mw1ENNipGxBS3peQ8j6ElPcnJOby9q7QZZXGJUcKjy/R5QXR5R1UoBYiA6s/JJXr+o1JhtztbkcdbWZYgfehbCnwiFCAbiEW"
    b"99TdyjwdYBWt8WAlRittS4ouQ7MetnbVsMpOws76CEvdDKtSkDh34PQOCXQpCzq5LshO43LreE/DQlrlyjd4ifV35/FK0Ifz8NN8"
    b"ewwz6A4Xx/Ba+y19O7Zo1XtfV2eO/uv1ZXzYYqRGx/BPhi+vF9BE6uMbN2vfz5jzp83js+WXx2pXntvJSjB1b3IitaVlFP5otWOz"
    b"lZVHbFjHeocfm3dXzBNLldPo4oXJy3LDAXFTvRWZt/It3vx95Zvy1bsO7CO3yzde4PHZ4uHy6enqvduVG4fNS/cZPp6S3bwPMGFE"
    b"nCZn9eUt886TFrxbmrLr1K4/tcZAWAM+ncmmizpm4goOBXDAAVIAYNDWl4ygr0LeyFBIqxp7hwkDJJuWUwgnxM6lg+ML22/VQCer"
    b"Sp3kOr5lQcltW5eVwTZt2FXZumH99Aq5vPUqxTdqCqPlPTBDya54zagtsIIu/UQZxM0+JXOG1u6YMrB12XrB2hE1hn5ryqR5HWTU"
    b"fih9aBukA87hoq4H1qjH6xx6wlX+eiAaDcBuhGaqKMVDAlJk/PgE5TlkAMXXzu3nNA3zahmy+bxirNBGiSulBU43H9j27fqZ7vnW"
    b"E7ugx0Jf3zxIfKCucd4+y3eswk7qGctqTmXcl63Ub/GzXW2aOOh7e8KxnaNGnhCBqPzdbTlyTDhWm7husSxQftTukwMI1xlq4w64"
    b"D7Wu9XaRkrNXn5+snJuReohRtp5uDEhNdsvtb3SaHnSsTka3Yz6S82qiZYfPiRsyHipoWYK8SBKGDXi917YXMVSFF9ELLyMaKurJ"
    b"vWpTdpgw/QqpL50OM8CNtHacvoUtE5Ugcj0t6RZRW5fgyrDsBYIkt7aioacpNF2y6/EgXf1BpsmlfUNJfS3E3s2Zdt317c0c0goN"
    b"2iBlCXt8jKzdFhI4QhbfYUZCWyJ0J3JT4OOpniO+CGKWnmx0GvxIXoprDBwqsd8IlB2QwHX7w5Yup+LOsfArX82HRb1PbSUsIVRF"
    b"/uFcbOSohWIS3D3nWGrM2SLVbHQhoDyHA1Lbg/4XBSoD+qjHg333e5KEad78Mwuqq8e9X2PFARnkoF+frEEL+36DiV0nq73xorzw"
    b"QGFka2BB1Vl+SZvVN8fMk/9YfXuzfHiRE7bihQLPn/q0z4K8QBEuGLtlFVU2I1E6P2HLJVBtwCHDbokkNwpN32oHIQ1a9yz5Dq5L"
    b"3L3keYlHgvQGZIQuHw90WlHWBHa7phJ5veeOI9/2pZ2cb1rhIa4F34sfn8tYrSo9XkHPs8Q3uu+mVNf6xh5p9ryClofh2+CsLDXu"
    b"EuuWHsjBCZNr8u0OoFeQGMOkLssTQ+PDw3QVknSqzVhcz5Yt7hGHGqU8XoJDOeDz0G0jKEG3S0kqmuf1O7SK68Cp7k0dIHhBk/Bq"
    b"/rSvd2vfbor6VAPjLKdnJTzOjiPisCEjZxjpvRQ9FDjU1JTY07+7r/ezxK6du/vZZxm1pVg0GovixczRVpCy6DId8+oF4Cjm4zn0"
    b"ZPzmYfnsG1DNyqfemlOPQeVk7Q4LvP0BlEuem4vACZ5hPZozzKowPWvOzwOA2GebNQwmunrBXLhfWVrUdh0sjeZz0FJv3x4NU958"
    b"d1iL/1eXVrn3DVY6sUTZU6cqC9cxgsjSAwFE5cozdDVZmPp58jB6six9R5eazJon77NOG4t3/cFqzO4oFph6rMUQvghhmlw2569B"
    b"7/DV3EVoC3pRfvmyPDOtdbQBhOrba5Xlh+bxS0JVthC35dPPd2BMEN+i12k/x0lK7Nq9c3Of/bLDftnfv11yBt8UjdpvMPvwnr49"
    b"e7bt3EFXidgvtu34ePu2Tz7tT/ypd1s/5Qm0X+3p7+3v63b5IxJ1FPJFpIsoel3qxQmiB85NFDA4INOAJ18dgt9Aw9nMyGiJfh+y"
    b"YXsinnaLkCfLGT0PyxjoCiVRTnIhqywk9KqeAlb+GOExQNW6GxZ0BGbb3CWLyra1psvSLTHTRvd63AKg4IBtf5JMT4razOfWThpd"
    b"pw6rkk77gyFfZwJPTk3HlNohNnu1x/VliwbeBkq/uuR+xTr8HR0UzcjbHs2MnS+IofHhvnWWL98rKRrr8XgcEBhKe0LMqX/7HoWc"
    b"shjE75ATe+kZVrAw0lDAHUMccIKZTk2b33+zuvItZ3qqnL1P4UqU4GkBmMJjTUCC5bxX1wvNyWxmQmf/7coCGpmYsdVOzJbPPy7P"
    b"3SxPy1m0DFJZLA9mZwC4egJypl3EKJT1KCEMoE4MtChQJwzaeuuKhFY2ACnAzO5bxODgZ8Um6WTjJ5k5IbLeNUj6JzlGWFfw2U4+"
    b"TnKxr0T2vu6GufsOCRengp4q6WmRXqrZzlUVU3L75YvdUoI5JaFa/Xx/vnE4qnORqOPKD+nknmsYr/O+VT3UIK2gcFBHkc9FxT5Z"
    b"Bt1pgzqiHkdPKcqBvrjT7uXrJN7Li9R7+WJjnZDDMtip/h0SGirNrBUwQOtUXqLVxRflJ0fY0dtKfOjTiab6Iq1nHI2CIpRwDwrx"
    b"EPEK1x+aM8fwnrPrD1eXTnOv2BiG106cmK0unnOs3ba0c/Y5RjFPfY9h1GTOsuzNrrgK8gfxRS7sB4BSsnsS38cE6sCIrcXxm+Ka"
    b"x8NqmLYh3SJWpt1u2Gn2XfBtZQ6MNrmVF06vKE3FWglgAwG/JK4yNNd65bvzlBKRop3aFW/RG2iQ3BVqN8rtag2MkrtCWY+lxpWB"
    b"j2aIgoLWHLOSADbQVK9VhhYSZtYREVfNaWHpgC7q8TmFiRTZBaWslxLdwP++mSTqrEknmfWwXkqN0n2V9lbh4/eppnqlXJJhJ7ek"
    b"stuEUQz1kY7tLIX+WG6QDYPGAIK7WLiUfNJjWrYpVbYwR113bqtyDR1GuARbGpq6pViCYY9lklZJQ+mCjx1L7o9HnXZEMSsgyCq9"
    b"HswAKsrTb1DDIQN27eZz88mRypVvAn4Wc0kRBWl03dj3GsvrgxVyuRuHVh4dbDKsnAawqE3l30FtZxtxwofyvCcNnj7KZIidxTd0"
    b"qPJOmCesuNhv5cF3aoyRz4DxO11k6Tr1hEnDRQd6r/nomjDVsAlGM69cAWUWgPNdIVCXtG40jaBBogXPO7XK6yVY2Jialfy/YXPj"
    b"aEOM/pi6A/sYQ+YbR/CCy7nF2tUbAGP1zVXY30CVb3qPlOc3p8xjC+bSOTz3jWkU43hS+7Tviy3BUXgQ0mpnL5VvnChPzWufRuId"
    b"bYqRYGYa3nITMDw+vGWt29bkf56csQ9xyz/erJxdrl29pbVo1oUoOIqfJ2f/OXkW/sf+P7wNQ1hdOW1fDst38fJhMF9vWz26Ulk4"
    b"hVlMTl83r9wgpR3kuY+3fZLYvPPPeCPuxzt3f9bb71yyOxTAA206G8ZR2Zfswk99IiZewDfpRdJ6npyIys8nCgLQRCG6SSmfssor"
    b"DaQnJvh5emJUfT6qPg81JXo/37pt55pD0Q3KMgi8qdCWlCDmC+MGg9wJ3+SupZpbuWv4xXmuW8918dzZIzApTSlB/hWwKQ9nRuhA"
    b"aiibH7IPM/dmUKXwPcXke75cVH38GMyYdxWUT993USuS2PQbtuTYUairL3+UFDhiIHT3VwOUbdT8nwMfwL4zf9dzqWRA+6vqjlQX"
    b"Xv3WWIHKlBKFPOAGvwyP4f6AfvlWgC5llxXO8vgWdiMeiOKJgAYJwDM7IQh9XM4EO3celjOsZXN6Fr1CLDzCinbjuzZ52cSg3u/N"
    b"+R/oGqLvUfSlmtXJY+Urz+w7jfBUYeW+Dc7lvMDO+XT1lhihdYDFX8VDl+Tlgwz6CV9lnineWpSXL4JYlEtmLRLM6cmi20smLGzV"
    b"AE5ot8K7zI82NTHLEwEfKl1dPu2iUsqOJPHZ6uIyJjUCRnPvlMyY//V6Chc6OsrEWnAhapWH05KzjcSkW2wWzZl70bDqUP+t8k+n"
    b"kHVPznDsnocny9ddA12o3hs2InALzeSCtgeGhCM0G0WjIbGXZtIH1vKFUSjQ9q+Bim4PmLXOnEUp2YIHcF10wqQhbHDweoCrCHcX"
    b"l/nNktCgjqXODgWIh6G/h/yPGRvOe9ha5uyWksxmg60U+ZNCP4d4Jx9u0v19Y6X6V0NYdOsgUXTU4Uh0uN2AdzJhqpnVuB70QNCw"
    b"bdDxOalo7C0mrl7HMbfgeLXq24tAuLAJq9x1imiTr3DGDGDHnpcf3ER+7Xh+AS3bJArihPnoskTarDwznZbPvkLRwF4Kmrn4unri"
    b"We3qNXPxlbl0ltskxo/7PbB/TpDAcoDM0fPGOshS9s4Sc4uM5x3J0vIbsimMvIzqs54wMy6xtdt0FVI6Rz5Av3gkyf/mkZDo4CwM"
    b"70gssy2KsqNJQ2Sfc1w2lJ1fvjmPBOXVlw9REJ3/Di/OW7ivjaazxZ7/QBj/gXIsUAJMfeXs/dWl0+yNWL4+bwt8XBNoFiW8l98x"
    b"5UikQvFpiu8OifTCsqv43MD2mUtjr/cqNtg6rjjsiePjiMOxc7Yjjr8LzpoeOEpnlLv3ZMcbye/G5XZDmyogUgl+srqGL9hHaK8T"
    b"SyY6R5XcIUTIjfFFCHf3WNxzlsEMGUuI2B+Wl3AOA3V5pD0q0nfK1+Z5ta8uL6+unOPOwTaIlquV5fLFb1FTebhsTp3B1OJLdypn"
    b"n+D+u/yQzxXLPx2u3D8FvMe8sySzTL7F1cKlwy8pwRYbNjwUKkf6e9zgHPLx5brWIa33aFh+43+uK7Ix8Ek8xdbIfZNVRcc6v/bZ"
    b"WsMVIM7f13ny9hu5qrlWyG/gqrZub7T6rmXcqf8zXcts++K7OpdRZTxb03pkH69miZSU4xG7uORzxg82yh35yLGNrDcZBLudS+5B"
    b"uNiB2bOp5Pgxyox0o/z0HCxk8/UcL+pAyOW7hqUHnE511+ng/++59is9135z5zDP9P9bvcNymVIGBJoJyjZq6wu+XX5H9zGvp5Xw"
    b"J7Ncxxp7igl+K5+nI7mENd+hqeMIrenUtZaT4Xo9uPx9wRRHVWPdZlCU7tbjtmWhhq6bV4Np+A3nafwk8Ue0o/wRs9/T2XMs2hXF"
    b"o2eUtQNt/L01GjjUBAW3927u266UYpugVBTlhnPHqDiCJNhcg4BitTAB7OYqhzCR8u2nGOFiWTarj+6Yby7gDdA3TpgnjrMIqqr/"
    b"V8Q10JuBEL/YAt+mmf2BOgX4EZmVyb2pdv2prPQ0ea9Q5jiWUUu7IEukom/Al1bpOtKRBE91xqDoJ+iIyHnke5e1OXtu9eX3jnh9"
    b"9WblyiOyNFB2NHsAU4AEVtBWl46jRPb6Mt9xLQfisB5o550XeSmcTFDYDycDFEmaAdFHOgTE/JVOaqUR2OMTad3g5EoipaU0TGmA"
    b"xfx+w2+AfglbMNzfF0sHQs498wQRmxwYDK3zamPWIIBmOaX3xzs/371lS93ZG8Uxiydxn/kM+3CvocCQVWtoIi4ZoG2Ls6R+Onii"
    b"vZ9thY1kX2HxokVMZq6SkdYwP+HceSbxxgcRBKP89H756zlx/nRiBkiCtLPDYo3Mfw2kwsZGAo+mrceHcV1Mz+IquLJExoQp89G1"
    b"8k+nfp48ac7NmvNnyqfelmfn4j9Pnqo8eKB1abUrx6k1toNVrjyrffsGe0zNAtVysxoZ3hg4EyaQKqxdgCF1wTrUIPtEdZHOR6bm"
    b"qa6V7hH10IuLdE/UabSIfvMQG6MK3Hb11g+opU6xF+EiFIDGRDjdzHTt5pK5NFeefmM3/PPkDCCkdutM5cnyz5OzbkyKyWAdFYOZ"
    b"5TSOQijyudHda1rIkG3WIdS/44GzCHB09irJy43Erb8L+9rfvc5tpFxhj1xGOtHJlJJETJyoKqvBN3GNVI3HkLENZ3WHLBlELAsc"
    b"dkKietDEMrmEnSUcB5fWs76Z3+QbxjFzsNgF0KEghWZjYCeWhcDWwaSLG9EDjdNiAumSWpgoHSzoPTGgOnuXkOnFnLxUm5y2Fw1y"
    b"0LPPa1evaYITwR56FggNd0/YIxYem1cnEQ6xZthb+NhDG+BDTtzRQ2EtEokMWsTDHad7j1GjZrIHesSs/Ddvc7Z+BGgxffSLW76K"
    b"stmL+1Bg9eWPMCIYS+3ij+WHtzREhwY0Xp69hUujMx6V7H02oQ6RyidymCeShYxIMEhoZ4Yuvw2EXBmFqZy0OdjpfhQ3geEhD98V"
    b"uirAFBk4x4eCxYA0D39Nb8Q9XZ4Z+D08ZAOWXwUs0zHAc5pi4Ph3oxYM/C5AtX4fEOW4r5jSFC8kUdppstad4sqWyDj6QPydbq2F"
    b"1hx/MpcfOOfqlm4w6VrjEltyS4p6Rfu/03UnUspVFxRp1v5eL2Gzv77ROEW/gidffCjXxra+0/3y/rkpffuvEpa4sfHv9uxh5ka6"
    b"H57NnpT7EugrTRen1EuYTSZdnEGM2qyHNNEUGW6h3GBTAziiPT9QMhguNmjlRaQkz5aFmcDwIDj3M1/u0mQlEEVejC+CVsUIJwUP"
    b"htyL1yrgXr8DBxyRym5drXrAqTOoTBJ2oN6cGDobdABJCfzOByrEQqS4VWtfUrUIvpgSJE3B9vFKh1hAyq9FXN9uOF9MU2DJAEET"
    b"aWKUPISuEsADBvbRsPcxmcSERkFI20eJ7RxQsE6li2B1Cls39JJ02+Y+YkfUSLea54VeuPDkT+YZeWaQAflrCT5r2GPykm4wz5SY"
    b"hAQiiefZgjqOc19pnQBFxk6RW9WdN1dlQoUMXdUBVTx9QqpApQLB4SdiAb5HyPBl4GUNQYqLCfj5AfpdUy21Z0Vyiey5mB8YQIep"
    b"Ub7X3tWh9d1c3XhEdOcFvPUZAZ2wZziYFulmnZjGopFkGi9KlQ2fghRtQwW+5duxrOlAOYNbjYZCiuQF9TzKJ5Z2qZ2ZXElWNMr3"
    b"b5rXTrFQw1oGB+mUz2HIj7jPSAcuRUYh+0Cy8noJFNDKwil2byPxR1U7lYn0WwqyDuorkDr2wYkxJd2x06tAqN7FCG4Fd2JMxl+d"
    b"zI2loFqM0dzkU05KhOwuuaaGGvWIx5hW2nJYl0ID0O1N3FUeVbPs49yRXzVGWjx+Qt4h35snb6CZh2Rb9jVjdUiSfFvYgezlWTQP"
    b"PfqJ3KHL07PCgwdqTl4GRay6eNWWiis/XKoceWUuvqodvW9OHQedDyijsnwJBdeLi1qsm+/GAlphc5OSDZqCPS6DyAsaVvmnwyDa"
    b"1hYmq98dZoOUrditHMebcG68QNEXFDtQAy0JvDx1nkeF92W9vAXt2uYf8kCim69+fAtyMkDA0+67F2Q1DvYA1vBQD92o8aD5MNMt"
    b"OHsplMV6dLyFucV38KAhC3OnwlFWgHA7TLj9DklcV7x9Q+9w85B1dZWPeSFkSdBeU1ZDWFir/pFyg+GOZdLCaCwuRRdnJCG8eT0e"
    b"prvYffLioxTtFq+V1YnzoDot2XJ33QAY6EuYOrQRm21F2cI3VvNQ2CPXksTul9MND2mhZUV0/x8UUeDLTZxUTOueSSvX+i5kCnsc"
    b"fmA5dVsI9fAPi3f8Wt0aVVUPoynPnEGNFXaIm49AgUVe42IoP08eZlUZHVRoTtADjlcb3WO9iPvdXtbDmcsAN7BZzOrLaYDO2njt"
    b"6AosTmQEb08AYxM6NmJIHD8vX6o+Poqa/vlX5ZN3a2cv2fEirDsT92DlXWEXHkUZkGkr7rRM6horbOxZ+AoNdLcOKoFmhrjX05ed"
    b"C+OAEgKIVaTTfl8KwkJNnrvGxMVFiT0lUOnGBJUoLp08A7XJefPqBQzSmxM8VPtsF7oGV9+8whjfN6+AC9OBAGL2zRWO2bPxhaG9"
    b"b6+J/dxKa6clEng4kkhIqbz07LCzWuzNq8kntt46UFd5okgG7HXc93mhQHB5Vq0zM8+vyc5jjTcCw4QJh7/qY6ldKVDGyrJvF7Mi"
    b"NJzAEfuVErbgc1jsFCJKI2d7t09FyKc0Z55SnO/to2S1uJMtxusRIbtCuKpJiUxRNMLMdqwb6WMsGTugB11Iw1upSY0kqwLdCxdy"
    b"KE4/UMgU9XQQy7pOFWSnfqcqBjfKcD/SfOK+JYou4E0rBJ7CeIdBvZO9WIeShu64fajkxljFEgKfIgOBfVkAn4ryaTdujENAd6lS"
    b"hD8SRYz4Dsro4+ZCnC9TEjyFHVlOgigh1CXNqkE1nkNZueaAz4llnVQUUhZwilNdR7y0U8XJnU7oXJ+KZJkNEHHWmAg9nig9LJTJ"
    b"BdXGCId6zhVeZ+zN4GW7DLvZLzKIjvTJkOA9uQ66EhqqyLVyJmIPsBkQe2IdXsvd77RgkFMSxLtCTuSLc7JdygvwsQ4lDaNjR0tj"
    b"9DbOJTazAXMbKO8t1rBm8hM31wr7zAxhw/vCOmy3OrPRidCHJTBgIZgWRzfPUrO1VGKDda83I9DrAoEuOzjQAdGDbiXGnop96OKA"
    b"Vha8j3rc3La7LuUhoLC7eF0SpPy2aqOeCV738FzM3pvw2QLh3jpsaO4XG12LetDhg5gSICESbxMvrBuYLp1VCpuRJ+zL2iQFFNc6"
    b"FEoGVFzvtiwHTKKr9D+WpCXhl3Mmud+1Pwk2z2WVaxA8foFWGhkbNRm8gmxN1HS70zH0aOrerSTM+LDHy0WNUr4g6MhOH6EmOvHn"
    b"aUPZPBmuaKDSPNpZIwCuWuNgRs+muZ7bjUokkhBxAGibssKNiroxCqxkIpPSAZt4Ca8TkSpSGRQHlcu45Kz8RZiUXDo/FsEPtKDE"
    b"ou+/H+tEtRA+u2iZSFzhnSqEKHivGf7Tqo/emHdOVJd+WF0GbeTw6qtj5sx50EHo+tJYrDnWoVXuLZfv4FE0VrDv5zbfHqvdXAbF"
    b"AoPhnt43j89gtsTLXzPAnyehwuXyj5cqj57wqTjbG/D4GlRktEXQqVzt8lx5YQkjQAmEOfcC5pCNG+gofeeZyHezMGuevFn5wQok"
    b"ARUH7z3kWw/x0Hpyhp1dsANvr1Tun0KrzK0f8Bz+zixoPOb8Ira5OFd+cBNUpsrpxyY0S21WHk7jSfniXO3KcXhlLtyHBtGNG68P"
    b"f1y78nz17c3V5WW035x/DJ1lU4r56FX54rflb0DiR6cYjt4zMfnPDYADw2cjTu3SvDn13DlWP3lSDJQuFK8duY2tLL6CFgWhZNIt"
    b"ZFDJZuGrxjeRV15/az68WLnyyFyhOH8ajjl/unz6buXqpGPLmXtsIR+vIe/7YtuWvsTH27b30fXsI4IU6XwsYBGpaBWvi1Yv+67v"
    b"h6LcNY06XCqZGtUT4pZpud11GmYCdm/oXtIC3pRrYNYt7lzQdX0hXVQu32Si3utsXcTsGZibnVJJYalyLgbHCnQpcqixkcL3FuVi"
    b"vVuUh0d9D8zoZkIcdHBY8ihOk12IDxWkYzOLPuRzhYxvUYeAlLLDCFmK0afrejxPsHVQAQMgrIgC4qcvPr6S+oU5ndKUm8luvhvr"
    b"H1rvJdqq2s7KBhODRQrIRuvd+leHIGRsYvV1YtMp6o/N9dNZEHtgoRI/61KXo+ePFcjBGprYqAUi8DPgQ3TwGLC9f700R8SWHh8r"
    b"BNc1aWFNpklYICJIgJulMaxnXsU8ZowEZqQ5yGednO0hCH+7tc0gwNmV3W5wMBOcQArLhvy3Sut0AwGLvL1C5KF8rQBCOvFUSzcq"
    b"V+/KVd/Crntl/QuxqUicH5Ht3/ZkWbsCRl0+PsNONWjkly5LUyuHnNiREWSjxTVFkPrMNDOGKdm08XGkXENL4Benh0CD47y6AgHe"
    b"DYQAkhrN42INRGPx1rb2js6uTcmhFPQpEHI7lYO6F2pSzdTk1JrOGHQ9aC45RubqytKt8rUF89hs9dkrzIYzfQ/PppNErF0dHXH8"
    b"USiAWlnklFtaoDPSGmmPtKLXYUA85jt8u7XO1vZWrDGWzGWGdWAudd5zEqt6b1OjyVxOz2JboiDdHRXAJGdJNrK7b3IPiG5mYezj"
    b"osyXo/g0j4ntAuIien4gDybWIZ6hA1K31opqrphVImQs41xZH3DeDuGM4NvdenosI72AsY8PJ1OwlDjr4p8zyTwXSBXGE8khbCaQ"
    b"LI51tDVPdCW5Ys7Aw/I0daE9jln6rGkS77DOgQOjWAI3Q93IZ8dLYgjxzs74AVDgyU3ZiwA0RX0JRIjziVhKpXSDcLI/M0zQLGqD"
    b"Z9ZX7Gw2A5q4eI5sgkg0gn/agiE8xUg1eIcrhHu3ZQd14kub4HqNTLJlD0zxyGgyI96x7QPexru6opSkMDOWcGCkchJ+AS0ljFMk"
    b"NDrTCvtBQhzcJAzQSwj5CAr4o3EQVusYTHHByoGY3ovXY0zkaYZSo5kcTUQxT1B37olHouK3TCubd8V7I0AMHdH2SLQ1FultDRxy"
    b"Z5+ytwID9oKx5EgmlSglR7C2gTQGFJofQdC8IuE5f4EnoK3mEjhZgW7OPCTZEd/HDJzR0KFQhPYjYABiN7Kb32ewFVi8/wqT5SXq"
    b"z0+iWMqk9hLK67bVJGc0k4/FCnl39lw7tSiMTk4sirkmYc5a4i1i8izO2fL7AOy/+4ywR3broUxGdQ7ZlIMzDxNoIQaiBbdncuMH"
    b"PtA+/0ATy16LdXygfTma2LLjA81ZzB9om8cz2XSLd1o/0LYUYcWUWvr7d+ilL5gCuqNtHe2dnZvaNVLgorHmeKv2x/FMynqf6ujU"
    b"N3W1tuH79ubopuZoVwinujeFWzCRa6GQzaSSuHBbSFeAt1ZmqH70lPEp84EG7LAIq6OHp7zOMSEwDf9zQpw87zlhdG0RXAjSVN/l"
    b"+MdbExKWjxCdgOfshOArYVtO+6pkqMJyJCY/YLLU6IH275DEiSFmxP78y4TtYr6E+5hBB2UNtC/LZsGrhD3a/KUN52Jpu6zvIZ6N"
    b"erS/29pvj1TPQZ6RUFpWYo7d+oJL0nVaccm79g/BUFRHuXq98zPx1O2nE6iNBVnKece+Ndnyv5zvVjpXxShfbAunizSYkOvdQMDp"
    b"UwBNpkovHTTKqXoHRD+pPINRcj1AMxYB7c8X94Ia4pU4G2jvDcYjEKX0Rl6qjvOj5IWClcLUYEhoWz46n+uNvFg95gl1npAHYMUB"
    b"6elgyD1pTinp8aDILfoexpGaDy+iPYjUgH+9nuotFDRz6rJlqUIvoPLhW+adWVRDHtyUDWy1I7dtS4+cYwXrvp4sn39szr1gOrMM"
    b"KYjDOqYVC4FOWd/12WCSfAjPghXyKeShQGX9vjPxWU1h/NKebZ/sSHy2cyuHngUm2kmEyewFpjSmp8eNpP07QMLbgZE8xqBwPU/m"
    b"aJE4mt/u2t33cbdKxYKIOXP1GOsG+OCQHR+fGcmReG4kyAlWT3u0Lwx+sD0RKg/fmPOz1RPf1yaPgA7J4TdIBwuT1bfkUQJ0MDVv"
    b"nrzORFC5N2sem6ounrM8NdjzDF9euF++dwUj3S7PYYLQC88qb5erKw9ks25U4/CK8k8vahfPri6dZVurZPY156aq3x2mXIuXyzNH"
    b"tAPNjEVOSMwRIBT4JAKFvp4zzzxFeyS1heZJsrayEos210v4PwG7v/ryDryyzbeWj4kgM2s+lPvZh4kTWJMxwCi3Pa+pADqlOETg"
    b"Wch4V/pwGE8baQrIV4UUUvqiVub0gCyIYDXF9iCVUyYbC4JmVdxLoJ0klB5m5x2gd2TkfpDWyVLPk6RNgBKFl5FR1Nky5o978zUQ"
    b"CFBBZXmueu9rc+oSms4fvFl9+RCnYO68eXUSbdXHZ9nnr7zwoLywpImr1dClkFPxlS/ck+mAXVm04X2Ugx9D0UTTL36sLV/EMNJj"
    b"T2sXHlJIzyXygf2+PO80h+wIfj46is5LK2dqN3+q3fraPHOSw97IOP2nvr6dnyc+372dTNMgloNUDrptZL8OciIJ5cnsSL4I2Bpr"
    b"IYNNwKqz9fM9vYk/9P3Fiv2i0+VR/QCL+oEOvWO4s6OjvSPVEeuMdmxqH+5s7djU0dmh07f2jtbOOAjIbe3DHa0dXR0xKN/Z0Q6/"
    b"0vi3Nd4ahX8dASdpHPUogXRPaWjlGETbSp7Lw8ZjB6MJIwhsLPhtKFMygl0ew0eXsHugZAwbBNn7XDpOSPudFj3wsfhPBEhxSbuW"
    b"c/Tdhmp1plTKWrtiIXkQeT4ieNfOPf1/zblR+tfcX3Oo34wmjdFsZigylm7nTLsRQCfIodBCUI1HGB1LpiI5fX/QNRdhxkDYBmWM"
    b"JuPtHaGIAsXQU3ny/7DBENywGNVGq8du7XENsKX8Xg4+EFC4mYHuWMdgvdQoA9EDre2DIXEEz89oBCH33bH2ZdpOPgVqT5YSSGjG"
    b"cQXFbdwffqi1hmB7ED8/+khrtyezSb2LxfJbt4D8jXE9QNfmiguIf6fF2q08Z9a5a9LQO9oiQx1tAlciNUskrTPqkkYqk3GCaSWb"
    b"JxN0UIQApR0mpd7HYF134DUXWDWFlGP9DB3Cc/xCEnCUBy04GAjjJtsdCPlbA6T843U0dodHhJsaqN622q2q+n9u3oobfrdnAbsc"
    b"KVzKen4vMqOW1kgsHom5g5nX1IKl8pICbCm/sahyASdFjrjTgKOmOOQ4WPsm5WbV2Dq5UpwC6jsE2DtC+afDLmM1SAWf9vfv0jYY"
    b"sLPXS3Hu44dczOdL8hkWcr79NgWKyVbOCIKf5zL4diuVoZ6FtS9wkdB3OrWAou86Hq+NHtgt7AoIy4orBYWWLvkNUq8pXCwkh6Mp"
    b"j0R5fipCnCiu3g54Ulz1uPQvjd3wuHKxr6QVU2RFTfhFFcHaJocqutwxIXxupTrOex6KFBAyqtPtKa7jQQee5Qr/x897t2/r/0ti"
    b"5+6tfbvX69fvOyz28XQPywpOolQJUlxkTty8hHw7n89KNexXrs47VSinJ/pjWO6srXHKEZQ7GExZA/OcTfRu3rK17+OAkzYRK681"
    b"JiQKi4W7GJA9X91ef3x5YrolrLtKKeFp3X7RgFJVNDC56it5KLo9qPemqXDeObHAgZAbrBRM1K195U3qv67BMSS6phhtHA5h8iMO"
    b"D/KrIgi324+Y61WiiCO5hhSCpBZ32S3fYyXpH5XTjzFPM18MNXW8fHaxil9+EKmpyVm8fPM23tCwcL388DafzlXOPrEu15AdnTn5"
    b"qnwXA3eSwvMQp4F0/IvsUOvnPQGVrjla270piQ2O55hCfBvWOaSEpVP+kXWzW+8BJqepwYTdlJ7GOc8UieVg7CPBAPVQuA2xBos+"
    b"QD0bDHi2iGrJzds9fLuGLU4APYfFoeKBAZmkBqXAXOi8K6TvKzksuJtKHPITgkjeAl6sykF0l+1wZqSeh4GfiGRdXuA6yPa5CwYz"
    b"k5+WNTlQ6asnnqEO/9NjRjAQEF9sQCFmV8xjd83T1zFGbKJda7G0wBbNPPawcveao07V89RpIPf5n92Lu1ocQNbo+I4WRzbzmdeF"
    b"780zKyJJEGUE1tCmxfklxHSDruqZZjzXDwn8SMaJWFd36yaNL1ATDVy4a769AGKx7FSGwTLs+zQFK+46WtRmb2ntmnAz08z5r6uL"
    b"5+BB+cHNnycP2/NwBwuMgryprS7dKV95C+/YWiE7hpXPCyubOfeCUsrerx29r5GshALYRuF+BpPWFcWr2fjycWhvdXkWXllGkve0"
    b"6uQMdIG7iC5isiecxoYd8/ETcmpr7dwUE5ePkygDIll18XD54mnAHTcHDIcNPatv7mGs4tNb9uXlTossDNm9x0Qvt0+XT9/DwKNX"
    b"1/lt+fq8jaarc6tLaAuoXH/I4UHs0lY++e3qyhw5+N0ypy6bU4/Nx2/MF8+Ee9s9+DtffnzWaZcDDNkqUFm+BKOu4l3oU4Bc+CIj"
    b"lKIL3dMAD2uT8+WHd4F8aoffosfe5HJ18gImAzl9Cu0QrYjoytI9yQgFrZ56y4nVEYtvf6hNXudVhDFOZ5+svjxpPjlSnjmC8zP3"
    b"uLJ8D5NxUgQUsvBH/7BDeMxXP1YeTpuzh80TN6AZO+u13yVO7SElrKGQ57BTzhqDhg3nFicg+DjmrIgyN7aLJHq390s50AFHyBEA"
    b"TTPTiHJa7Rstq5v2z+PfaJWlRcEE8BezAZgLvP3gwc3y9LdoDubrUeYwHtn8ZoZVOPMRUm/lyksgPQtt9v4GK4ZNj2wB5HUG84cu"
    b"jVeeoY/hwikgMdzovv3evHuBrdCAnNWX09XJY2jZ+8cSMCyAY88uXlF29a68x3ECSGERFfene+2jrqwZfqHt7LnTozA3iZ8wBw/b"
    b"cxJ2WvVGFrjNdo2KMstTNjEsjrsYUrC1gdkgwij3UY7MoNWXUCSnl7L5lE+GPMGxaTRNjSLxPSx6DVbtUkrqOmI1ypToB8zX5cly"
    b"1PKHxSj0fcW3QRFuMVXWhnQLcQ4bw8DAhHWbeeCpbyrLVy0hQqAfOKTNm7lYoG5bMFHW4tyILuLSrDmkVH/+fOGG1pX+BZ3Vo5G4"
    b"9r7Sg1BYi0ZkX6h1JoaRT8n8T2/rd4pXinKORU6HrrMt3zryqZZdSX7oHkgQbSZC4+8tlYqZofGS0Pr9eiVg+lwSRSGL9ncp/TPx"
    b"Vj/Z1cfhj/3fe/A/QSq1Hy6aT0HIp/TctE/wPsiFmhTZxBI9LiskCRsq7cbA92grngIRpi32X/i3VVzHijdosiBSfXFfE0ID8GWU"
    b"FabZ0R32OHs7Yu9wqCAufAPh5uEybFDlc2co6dw1ZrG81+F5y8wRlivERsc3S85M444pbXp8RU75wnfiOtyruIhJ2NAwM8LJk5zQ"
    b"APqAnvTkek4b6f3y1AuQb1DyoF5VfjhlTi1Xf3rBeeOaEn/q3f1Z/XM0etu7pX/bF33dmCnGzhfDb/60bcfWnX/Cy2e7opGoeLht"
    b"R3/f7i968ZSgLWJngdifLI4lhsaLRmnd4rsaz+06lGHLRGCD8Z8e6dRKtSMd3tijVAw+IreSPEpUL9EKIT+jvOTxhr6/cnFKeIKG"
    b"CCn8sjgubhp1e1Ak09kMaRyyn9RGTUZvfWbAsTZyzQ9tkD45Z6SbKJWJCq0/PY3FqKy4bwfpdIgs+ACb5VwT8e6ZanzjJdfYkwIy"
    b"H1DVVkw2tzLLe47MBJiLmC9+BBmJz93s1WLOPsXEsrRa/Pel+oTX+MZ0F/3Iwoo8AGApr4+uNQDoennmMLKqDWnkTn499esnp9yR"
    b"SS0kbWbDeG1D1k1x9VaT70JIZ4xUsigvBjVZiM1u+ulbsJQsjuilHlwtQFBJfSyfo7yCYQ09PHsCoyPNyEYCITZkBtfyZW/Y2wY9"
    b"FafD/qT+blzLzkLB9wyr+QyET5goD0Wtb5i6y/oq2XO3b9vRl9jR+5lIJMxmIoLOV1dTSM+7MUZ/lyRxb7fbjWfAudF7UNERBCPF"
    b"NHLW77AUFc91IpQ8LMjZ3NCqZwW9hwZdjilWhUK+ECRQTmZG6T1fQswl0UBoD1++MJkK+nrHSOknoIxQSmu3vq4cfcibMBp+bCWT"
    b"rqfCc/oLz4WyRvaA2pXjaD88ex8G2syXm4NWfGp1GVTfZVjDjrrLV9Wgu8+d2fKpaU0VcDgTLhpGjr/AMLGToDSDFGKIwLE7s7C9"
    b"m3M3zJM37PvlzeXn1bfXpeSYDSbUunjd45cFm7m47Cfo3M4eRu7tyIITnHLeeu2Ha76mVAQCcAVxpYGatCKppJWToTu8oA+fuG9W"
    b"FW0P2O0OWg3JhlF3A1Qgsj+ZAS7nd8V9aN2uUjbF1V0P9dCyFhnWIUVJMfTPtKReOVw+eR5oxjasYVDkd+dhA9Pao3GQXIV5aPZp"
    b"bRKvT+IrDm1SE/4ghy/bhiS3DSDhsaTEf6nW77XiWrzUZ5Pk47uEYx6WUy/SX28lK0tjvYyNXM3nllxh0JmZZls5GsPosiq+OAgj"
    b"SWn/LZ/+Bg0uM9Owalm+Lk9P1ian4S2WOX23+vYMXhaz9F3t0iw5g9n5bp8ihFdPasdmvdnzJ5KZLN+U4hxYei52AIRYNvQ68tk+"
    b"HLaTbN5OP4lVG+RPdKfYxOJ+6XF9G8XUXPvoAA8+rIS2NJ66qjy9tg7hEvt8E79aO+DaEBkadF4HoSDaQA7DkHGMIf9qX7eW4fPg"
    b"MCfOdFxF1NPT0CEvEMpewJkA9hJObXlq06aQ/8zyxQNAjj3Z5NhQOqlBB4JRTtHZ4+z7hOdYWEsOGUEJPAHWmrnlkI8han8yh/6h"
    b"Vm5QatInDYZOh5uGkvRT5UNJg7icSEXAOqU5dcVcXhJ3N3vq2LfNRZs870iMKiX3YkYBg1Pmh6mvjkJnp+DyCPKBAKux5qvnuCZp"
    b"7bH5irvF53boOHkJbwmAAmhIBk3cNoUuPsOjrbuXJV/FdSs6FtePOMIZdty37Pq0GY8JyEXuCJ7SmArpsS6Qhn3mKUG5vmERwvAA"
    b"B+gNaqBbAB43GIBDxyp/+ylnBUd/QOsyVORoU4+54DcPzRNLgTVbUQRQ69YMddU4qXGV94gQJpdQqGEz9d+uf2Yazs4a0oHHX3pd"
    b"crOnEVLmKesRwiCjgwXls94/J/b07dmzbeeOPY3HQHVJcM4Jx4GigBdyi9G+VVUJy87NVsfyTe99tyqiZuCrMmeqs2UJTQFTcelZ"
    b"zBhl+cTgNicIwLfme5qdZl65PeQy3neycN9+CYIS+kQ76fzY3dXOP193U6t3u0mowQqXMxW6M4y/+0p2QauTC5GRFJZT8f9ma+Jd"
    b"xoMu3Ur5uhJvHXrizUKB0YgA1D2rungXNwG6IcZKrYr2HFDabt7mGxFWX10v/3gTfZ6nHmv7xOlPXb7e0AblJsCFB+Wrd0WSWqI0"
    b"i2lerv70mJ1Qqi8WOVutSPx4HM3BLLBTx89z0sg6Rzr7E8LHjJ1TMCU00aJvcfJLoSVFDip8OUL94k6uIoTbvTayxRfydqRv/6OR"
    b"0CAsFeuMjP8NJgb7JRAmElaT4NP9y6DZ9cmyKwD7I5KnSBSp1zVLK/kVW7wgBd8s4QlKSWU1YmULr9shiSd4D2LW04tGwKUVIjI5"
    b"821d7HxF0w1Kq+zUpsn5ltHD48INn2TLdRpTVqGaKhrVMFpe5IF6hi27YiM4uoJrceXb8tT8z5OY9JvJEW/LmbrDNNxo2RD219oS"
    b"pGypjbOo+qQ1byD/2CxXhv9r2K4E511Zr43x1ZXjNpeTmeFvsLKtrKJR37ci1fRQHWlfyTsafXeFQGS3Xm9y61++80oNYU/DdUeE"
    b"95gSRkj7Xk8+az8lxzJtybZpQYweT0jhFk00HwrXQ0l9onlPxDDhMcf8vJy72L6am5OU4bVwy+ft6+9sHYTSHrMjE+cVo1vi7tRt"
    b"MGEMp8SKk5OHi3FLmQcbLjJyw0BIaIbBzzVSjq+52t59jRFuxEJCL0zpijx7YQWxb7Y7fxYNbc0xjMap34oaNd14jdsX97EfKV/U"
    b"tuaiFiYCT7LVd5YxGy7O31pWfgetfr39/2Xy8S+TjSm8kvAOemRrfej+V7TWdSpmegj9W7yd6k6vchFTG3rhJGQ3nF96vqzo+3U8"
    b"VPxyd1rl1uGCXVcktmL0XGesdU5J1mGA8Im3Vw90yChga/d+xgA+LmHTYFNTYnfvjk/6Ep/v2NPbv23Px9uQzyEfGM8ZwFaM4Qwm"
    b"zA5YGd/orms+GiBlQ5ySOrnPPQn3+VZ2K5H+nWeUbpHy4AeldKogAXJa/Cnz7Url3F0Q/0Bd0Pw6J9/KwinIRCwfm7gjuOILwVAk"
    b"m9+vS1kucKaxvBIcwzctNLr2wijouK1gzYGO7sGIUchmShhAFxqIDlpt2Xe+Nds3vWG9+lCz+jAMvCjO6rCsBbgZZjEWUk+7hkue"
    b"+CWq6qQkWTsXi337N/q4od2QIFg7uycvHhf3Bes3J54M5iSsNAswYft3zD0wvyF4pkBIcthrrCPcAShc1RkJKYMqVlgfVdsWueOt"
    b"7Mb2S+mqLmztox7plgp+oqa4XQsZluXMJnHnrgP5QgwnwYB0XQ0oPkKLUm6n4BsPpmzxm/3SpFsqTl8v33jBek/dqw44569zLY9r"
    b"5aq8sNH1AJaEToHRKg39n5AJf11pjsXV7Na1RO2xOOWuirdJ1FjIG1YUn18GZPv1GjmQidrswhu5YW86bb/QW88dMvLUeCOq/INu"
    b"7dOAurfMWJ0TKZbD/tV9L56pU3a3PqyLFHZWdi9KWiDn9/K5k/hQ2NenDcN0W30iyNh/hx2IGuRh95U66oXxCiYejGMquXi0452v"
    b"qhfLmVax2O5Yeq4fv+s2rXMibDwGtqoQTQsdLdjR5qVV19AIQn2RsF7ebF+PMJk4I6ls3tBdB4vKOskXKDu7+36XT0F9zcKmjNFY"
    b"6A6+m0lcPBYDAXG2lE/ls1bePBRGsHBLLCKuPsWccIAJ6f3oSDOTgcTysnnQBIHLJm0W8H6yOCLd6O3rJ8Qpt2y2iTHzY4bDpfxy"
    b"bbGMCYJRmvkk+6XTAnUysbIDmF48SN7TKEXtM4JcK0LPnWLWORpKNvTKvieOz/GlZ9ajgUBgEAUS9zZuO7MpUyU1IHpA+ZWLQgRp"
    b"IRFkoDlmSzuRgALciufzhJ7CSrdhQw+s7+4d2RMmKU6CoLo84H3W2Mj1jcbnCdV1cj/JNdNuvLjqKemg5IqZ+hUPSVQxnMxkBU2l"
    b"KJkM7SWC2OQsJD7bKWaWTFgrKaguf6cAM/GgmtUAM12CHNpCyqE7q996oGwncYxvyqIgbNFl2dfAt3ZOT1GAJ2X1hLXvbs0pbjSK"
    b"aqCy+zEdc4Su+bHbd0ck7NzjY5bmlMXWJKTziU/7erc6S5NwjYanXH5fslvb0RWNw/7K8pO59C2w4Orjo+aZFXN+1nWbAvETSkDR"
    b"w/dxK6180tf/GzfCxgiHnOhVIp3MjSX3jluX93A+GxCKfAgJr8aibEHm61fmq3PVF4uVs09AamzBRPJjv0c/4kjkdwZ/DI+Veg6M"
    b"Zf8Tc0GAvMhlEml9aHxEq574vnx70uU48Rvzsl/DxgxPdaNuWRgnJZGQCsMjqzBggMuTmoi/VA2RJsPTWro+g/WUzazFjEVGllA9"
    b"tY3phHhLW5SMwWMZUBJyIxrhrFFcgtWCm9Mz/nC+gcYyGMw3TF2ov0QTWz9LfLqtfwBKDbpk918Q/pQoFDN0eQh1AUOg1OatLOxc"
    b"TuAR3Yet9B6cDFB+TUFx7oQW7CX54CbGQYro0inzzmVz9mT5m2urS8drl+bLPx0WCpNliMYEAQ9uYhjz1bvV79DmjJ5FHCRMYQEu"
    b"WR56L0aCHZlARxeDQyI4uSea6TKlHpT2EYvoeYr3e4CODeJcSnfZIL322HW3YEGX8Cgu1iYQPmiUEa5u+WTAgC0fMwGlhVWEeIMb"
    b"xU7KKp+0EvbeT7n7KP0Qp4DGC5fgF+411CEftULMaLfceTHJbNLBbc9Q3zfIJ4HbkMgnYeDNhq4cEnVveuAUSmKUqCIa48X/l7a3"
    b"/VmVXfvEvj9/xXYrjMJmjwqCPCiCiviOIL42D4KIgoKgiPKifprMTJ400zZp0kzbpJN0mjTzqWmbNJn50L9mZ6b/Rb3Wurzve629"
    b"7nvvp30mK7lyXSzO8wDO4zyO3/F6GqsvvZo+tcKvdk7+Es36yLP8gKJ/qfvuLxjgtRhfhNZr1JcORT88huKDGy7u6kv/3K+f8P83"
    b"3e8Z71tKL9n4lfX+WmqvAb9K7AeQ52VT/QMQzxeK/5+wzZcj238T2LBfGpkjHzOcXRth7ZdCQITzSzZ/QTrQ7/+zoKJPmfdFwf/m"
    b"ORN/ET39fCj9Pww6fWKRvwJonF9Gt/FjJPDl5zdtoj/u/ca7+hVq/P6Hau5bzPOl+ddfoeC+0vhZUv3R8bDf/5YaxT7U6MfI7UsS"
    b"/QUl+tXWex899Tb9fnA0zcf1/+KLzPu7fzQN/kNF/Ong+tDHX5vW/oJy7h9BPf+AxX4Kq31XFvXnCcG/fJg/l8O/4n36pcX2nuEX"
    b"9cy/4kj6xl57D/tlRfNf5UR6D3xbm3/3a+6iHwa6ftn67DML5e///rNy4F/9T3/6H/7NlySvj0j3n/7n/+OjQuBrFtSXLOWPdLAv"
    b"dUF/+q/+3UfDhn/5v305Eep/+UhS+7f/5+vnf/pn/81ryHfzf4nJ/7QkH1z1QuUfEOVf/Yf/+F/+jx++4X//X//pn//r/+e//ddf"
    b"+4P8zQ8Dul/K/kP9u+jIx5+vq39crb44aFar128fxXer1d/8FRWYn9bHR3u3//DvP6NeX2DXn5Uw/u7rt/ly7cun+Agi/80Pkoe/"
    b"ZacfrNXnG/3h6zO9z8P6chLLf/dvvttbue++5K9Ugf/3nxUx33Yl+Vr99cOWJF/rQP7T//0vfld4d4z5UkX6sShf+ut8TWX//tzQ"
    b"X+nr8FqUb6sxXlf+8P2RO18cJj/9nf1czVzuB16/X6/m/UVR9m/krP/mfv5pX//FLfxXbNfHH/7iY/zKJv3tXPDv8xbh3/3+ZQh8"
    b"raH96Pz1b//ZR4XPL6qBvyz3xyr/6f/63z9Sif/Fv/vT3/+vP53B/ecL/cty4Y+GjP8YEenvFEcpX/zD77K//9Hm/9vffbSE/QzN"
    b"f49Gf1O7fOTufQmGvLXbJyz5iqa/hgS+r5X6jD98rbD6ZeD3p8n+8H6+P/55EPHn0Zb/wyjZDzTntzgR+/642X8c79hvz/T1U/zh"
    b"MzryO+iffg2O/Mp7/pWI9Pf5v4b+b6DJv4Aof7DgP8cdf44kGZtvF+aLaPmoo/rm7b6NSf0Qv+M/mOcfhuq/9v34p1/Q218A6N7n"
    b"ovg/rco/3NX59eTan06Nzf2YU//2t9foz7Xgd0zz5zd8ZaIvIbZPRvpFzsP3u+fX0Mh/DlPim/jS+zF+GTL9OTPjb38cevylHfJ5"
    b"tOp3MjBbP390Yx5ZP/WW+ZnJJeO1NX/UYeZriPeD/T8CXZ93f38QwW8L2d+c4qea/9f7/QxxP8JJX/t2WMfLXzz54kOjf1v283EQ"
    b"2/e2wGeQ5EvrhR/dnfum8vbLUW4/Vd2+B4wESf4qOz9CEb/7weXC3/01Bbpf3/DjG7zLrz8CauOv7539faFI/DH/+lf4/R++PMhH"
    b"hdY3Absf5oH90ND81cTer4/wx6/dHlZfy8D9H50w8WvdIj4n+Go3vj6Zcf048+oX3SO+7Rbxw3yp97f/8Fu758tv3fiV3NeTLb78"
    b"+qPF/WmSz7/zn+y1xrFfpEd9f870Z9bS15avX27L/Xwdrv7u99WPo8izyIcT4+Na7iU3sNyvNpL8ud/4Zz7olzHftHb+uY3zyya1"
    b"jl+cWn/8fvt9O91HHYS2NVbfT/v5gi8+1c2VezQ+O9x//46fksnUfO3yUZb8/YAPFfDxUL803v/spj9+zeuq/s6OHe1LtqvjvdSQ"
    b"n32/crn0+Wyr+ms7NNorYcit6uXSt31Hf2Xev/mb70Z9+PO/jPsnyczDymMlPJBVvs9wef8y0wi8MB6s5XJmT0nIbZikFdMNtoTY"
    b"6UwnRIW7QXgDrYFXUSLUqRUOOss22Y7isTTMbXaXUtsXWnYOYnBzHPLOqaSx/+QrKfGky1064OYXVNdqDKzAcLmiXjczbVzQUkqW"
    b"QT2rPVQmTUNTgksMOnh5dOvlbA3C0AnkDBfyk43R60ySyAETkIBK31VXDqask+DztUVU6kn/kxRMAg8uSSTsMqOGGUsOgtGuqwbU"
    b"ZVk7cWl8m3TB3SCJbbcxX7o8Yp4Cd7BPdwr+eVGrg0+PDHfrSbxmUiUIGxOOBkZp2pq4sxx+7q7qQtTveG9SodCMmpzQbk6iXPus"
    b"ZEyOczfNjLnmz0uxwwVlVV6v2tRzSU8Hs96s9PQQUxhell3XggLwIlQdnEy9/pPgVHimtoBzHV+qNNmFxl2AjU+7o0btP0l5UT9c"
    b"WlSkd7XBc19xgfadSN3U2iLiHMLCvcFxFgY3LFafdXzSk+63BVPc2RVrfu42N8mqAGVOHmWtB8NH2OlXIN7KaJ2V7Arlo9Vc3md4"
    b"EBdSn6SAnLAN0NNWOhXMgrda5Xf364nP1ihtROBpFYGYmS+vxzpZTrH9Mnq7rLCTMmyfxodFrQke3BJqrZIWeXzaqyRUSo2kfd8O"
    b"2M4c26q3NcFJ+yUavdcqTU0H7aA0qnavKBh5CsKOm/J80QAycjgkjrU9Ug39RR4n8Ggg5oyZsTjwaLdZoVf0JWmbbCdsKFi2Vgan"
    b"+iSsBmH2dN7pHXY+KS1cX6/FhUz2k1TrtB3dc8XM1ciCj+BGZYNwI9AcvhkMjopKkIbsNFb16ukg1JWoWmDLvmhVBrvZc9vczPIX"
    b"LFEqnf1A6dbCCrgsDHLeQgADjk1F0q029FacayXuJ6kpuWkCUxYPoR29T5slCnvA6U7/+EynRbM0LSOArTZ2epQPiKaUGmbyhJhP"
    b"12dL0tJHFa00sfpQe5y2ZpRoSUkuuJRBnbTWjYuk+Ih5DeVKvdR5s8WyBVXQQYyXS52kVD/mUYNgwCYQGloedutWp5pmIwUtN1GC"
    b"ACpiMFgiAgTIV6p8r86JA1OXyOeLf7g7UwuB2BbRIUfi5TEFLxihJ3eEwlES32yRGdkOX8S5GQ+afj/LlnvX+AyNS2wE7m6SIvol"
    b"bnS3na5O4cY8KcEojczQkTIXF4vcfa5VSteMonr3ozbtzxQIC2lX3mYetSKQ4Ovmg7KTm/dJajIPQToRKt1n+LjT2dS0UPZINKzP"
    b"ViW4nY6MII9epT037s+bGZZMoql42+c62aFrCrQgneX9iGOTWpOd5DfheJ7qERhRSAZ6e34bWkibcqHtOPkkxSoBUIvufDsl7dNR"
    b"P+hf1JRb6W1zi+zSG2JyjFa2gprONDli3UIA99T0LxC6as525ePS4rb9vLDLVCxyLu38sFZU+Bdf7hf9xfyu5S4sT9818/0Bs42r"
    b"jJ3LRx42Cnp1Mi6lKxR2sgyx57Qe13TfOpe4+8atNc3hsjnW0OLmXu4y8H6vgSM+/Uh8WmQvM2Y0zUxqp2q2MOdIPT3NrG47eO2B"
    b"U7CeM7hPUrc7RwAgU93OMBzoifLdDBE8qxAMxY/ZQLSmbG+2TzLVYaV5cGE5UJ7gaocdwMsskmHJYuuGD+hJkbeXVnx8Io4N2GDb"
    b"aIjEokwmUNIyW93Mmy3YvFwSDuRCPk1SC7UlNPNT266QKM9Ortwt2abT49JQY1YVENkpjTI1H46o7tHHRphK8qAQTCOylUTGg/SW"
    b"81ad16YJyZ9mvtGaz5uHK9K9nNOfpObqtQRVpo+AmMUs07c7nYs3BftA8xik6qpsx8pWyNxBjNPPyrbE2PfRAarZqpg/qFU12yUf"
    b"jjxKueG8dy/BO9pqadM7olwoegIbkPfwJqHP7z5JSRWqwbAVJl2vFdadzS4TdeCIxdlwUUT1kVYosgSZbl1zqaqZH8K85Od7uzxR"
    b"Vh/dkMAPB6dVrBHqdpLpX8oOypTo/sQjcgNdE1ooYBtdccBmp5+k4vSeGjUyw1RxcbOaXqa1WXJoHc9pw/piomXloeZG5fmzuo7q"
    b"bW2tQMcrCUAPaVvCdG21zrNzV1rxqMbgYnrZ8iYKXnuiYxI83t2oKVcjGNHG5iep44pxwlOe6h06yRCrasI+f0N4Si4kpft+cnie"
    b"vUXweB7B0JgLQykJmVv1FrqdvWCiin7z8DS0iodx78Y7F2A3Js+1Vlkf7Htyxq7f12e4VIjqxU9S1dtySmwjopmo2SKZVl9PJ3Y0"
    b"wHRylk/3mqtzlF61IaQF3Zc1QLyWZ+c9M69u3MSrQiHaihniNiaY/Pr5RI7MZLsxlKh/uogNp5YX1KaGH4/IWzWeyZG7K273bOu2"
    b"qOwMWwVTcKbJDpv95Vbt9MwdVl/yow23mBeOqfJ5DO9Ewh4ltaQnYKWrPwmKmzEBwTa/1g+1PoTsyILjcdoVmALdRYFyGGK9/iSV"
    b"epYhJjtyOmHGHGC5g9hMI0PSXvmT8sQToxOVThV1Ccf4M/lA6x3nNM2OUh4e3Go9gFOAp1psQSNk1hHR4IYcOgfMqZQZadEqzeC5"
    b"6Yqh6uGHn2BMJ51wjzLd6R4iETjhGIofW+Ql3fdj6rHOmF4pWeUyq+ZtaejlJhh2vQmWQrL+Y10oFIedHlGcX67nMz8vFh/RE11Z"
    b"ZzcBB0eTk1m4qfVqc+utGsV8dwVuWka3lCa2vfThQhiKweiFJmEJ/oZYZJ43X5K76ZN1V7JmOpptio9WZ1Kukx1eiStzAlMuAoIH"
    b"56zSWBZQdqZOWutGMjIAJud2hlhpcHrrq1F7cyKbqd46NqBRzUwJjRx6suopu4aRs3Etd25fXf7SCjVPzd0K1cu2zA7EUmd75tEU"
    b"CWUD0aNBhMwTOSi7T2VP873VX4+U9IO531D0gLWeKuF8kuo9t/21BGxqMWDa2QE0SL82FWzEYBPNdJuLXYltFa/NwYjjijy1uSCj"
    b"1O7CpU5aFysA8j7cmWOmU5/cJlxnXa/f2S5WM0+Pel+7dmHl3lJ8rpx/K/ygz9bqJH5MLSwdJvczEV9r/fAOj/L1faPXHeENp9e8"
    b"lHjfn/kF1zi0eczahn22x6uQsda4KlI6uOtB/TGKKSkvcachEj5OKDDL1KF9vcYlLFD/JFUcmHGvAARu4MSFi6epCanve6fdws0y"
    b"hXucHeZGBn/tWGv7SJ8PY9a+UIy8X2K4M+WQUShIBYrKN23X8yJ/sbQrttWrSz3pUiMzi5FGwaj8ED5JXQ7Z4rmRZDdLUY0c+Hwa"
    b"KffbOS90aAPn72xqdK+t6wWZuDXW8TZfuGSP3IQ/t2Z7Y2CfteXjKQDz40sWqZ19DZ2by+4ew87KsapMC/AQxOx1yL8/YD4V5pig"
    b"IJhFvlQq92I3XoXSVWEkeLxTGzHBQ+3zOagEOXQADtqGdp64ZehUlZ37iW6lN8tZEWT4c6lN3OY+2GfjGnbjCHVyq8vSwRgskBv4"
    b"DN+YfTG6VF8PnC2T261nSMxGW9bbNGyBJCvO4zK7o8XFM9dgU7rT3rUrbFO7WstcabPoBnv4YYZ2W3OPpmrHXOZ6l5fFVu3yKFg9"
    b"/IZSYYha6qH01sLo9mVHmbkMubNLpLc/kqlZFGUb1tjJbTvyab9ftRv4ug6Fp+FkyrQAhWK7fAIO04HXjnOnpGjwl26CTi/Qs3bE"
    b"nXWnVEMvFxA87O2x0j2oJbb3lhb+pQG2Ug/jCmaj2g2s79NevxIGrdPS3jVGG7ZaG13z40upQTKqpwDwgx5N1cYAA2dzi2WrHkC1"
    b"x5zSKZtRe820112755DZegU8X8POZtZNSZo6+yRl1uXCJp0YaVqPyYj0J+SSbjVLMzOobfbRJhMrfZ9xnmd/lUZZaJqpmS3bEXAv"
    b"H8TP8m2EIH0YTMskMrfmvS7GikD5nN/3CmvchMiZlUGg0sr+JCWkd7tUD4iAwMn2jpIj5KrFrq234PnDHBH8Mbky7AwmU3CtiYE+"
    b"uolv3VrlkW/ELb99y3XUE7NNhw8C2OXGjaslVTfAICU5QZ7DsZxXzrmbZ5f6JKUG7DREzTC7dGRwWS+1hqv0EBmTnJvaAXwQi2tg"
    b"7WoF9lyS2gcZutdaTbmE5s/hOtzE7H2yWOdv47oDEOKRORoGs4urdDipVpIVchpvb6XA6r9JDW7FCzOHOsy1tIsMgWLjm3I9nlL7"
    b"Zb9iGI30gncjCWi1+F0vJOiGvAAWSWbPHeWJ6dgcfZ1pYCgpG83o7C6jMXlhJuEALjWze/Eirnpph06syfsD1vrZvn9AK2APnDh+"
    b"aoplU/kExGMmFSj5DlC0DtdB0LjWBoCrSBPM6pMTuyqfVPHELO47O3Fb0+dol6CpSzpfo0drhdneURduHvQ+qlYnIEiSb2xRsLwJ"
    b"dcjimWFcxDcoPCcPzeJco3LUtnpyVEsupxhQDCC9W7JWTHtDzTBhWEwrzPN8ubuWxHmbQqznt/1rP73JZnsXDa930Ct7RKZMuJzi"
    b"td3tk1S9BdNQGl1enYy1zINQHwtbW3qEl1o+cwPhRvo2UHysYEtdW6ZRYdKD23dlkLWTnXNmnTQ07bhQJ8nhOXUYn/HU0bmlCZvS"
    b"qpR8xO2oeB0T1bctjD233OpM5kgwQ0jHsaNN2rbBDXI7n5dyE2PUKS4p4ybka5MEa++V4dgb1ZY9eVw4Rs/XNsYtqHsddOrhdu/g"
    b"qX6nzM/m49wKe/KjvKyrB0Zq229sUWtDUZyXXBiQ1O49aV98Dghf7HU/QEnJXYXLbRPB1hfjHDQ0s2B4TOFqX3ElaESFh5psvRlW"
    b"ZFR4EFDTmp2JRsF+U6vcN7tsND9yfiOXLtSyb8we9zqp3KybrFwEjlWA3jF8Y6Y9rmS5YN5vER9WAXfoZjC+seR9/IJknCiRns+p"
    b"nEPul3woOK025PDQM9756UsdHFFLx/XExlMpAgc6yW8q3gP9JBVZgThJH2zgNGC6jFvwM/ka28nAmnoJpO5lipnFsNHUhAFbxHHo"
    b"OHhwxYTKdPXpQJA3NncZdq9MrYMU+wBTPFWnjck58meDx7YFWFozb8DeJffWV2W9OR1bmX2eRFfoHKy3+ut1xTD3CN25bZf3snnQ"
    b"S/jlaIHFUX3sbXO0eUMb1RipwQdxnd4U8axbIDT/cKJn2Oj8oPKpLpdm/FBokU5UzJkVSn+v1UnGPT4DHHB4W22ZM80hH7oozZfD"
    b"0s2eZIBJ4aovk33nbAWKmc0PoFA8O881Fl5hNleEzOQOCZNlW/Lv23uO53oaCO2euVlRvsiM771QxLPr4W9Tbp+JDUI0kRfi3RBb"
    b"qCJfNRqjqJZZa6pewdLHZbwFWSwZX/bIrJmhCRLY+fV0obXmkxVd6vsLrTbHSabso+EmWXPnyvCZWdAqvpjk00GYz8HwJ6kVwHiF"
    b"2XMclJ1OAI6b0f6Y4kvi+V7u3Ydr8tFtdd29COOeQt3gQMbtY9S7LMdV1LClnGra9LE1XfkVXDEpOItCWG7RWlPByCz6XJYKD7eq"
    b"m32b3efFZYiNmXgT1QkwXmkzcUnlgTwHYeWBymiszG0kZlpA4T1VWpjT2tFqw5MK2pmOcwf7fqWPlDzBueyeL2OOAi0vxXYLiJZ4"
    b"niwWzsXSjXWN61sGbp0Dg7dM3u/Yg16h4U/LXQer0cjDn2HHySp0rw9AS0Qqz9dtGgaQ1PllmDpn4Yanmqs4Qns3DVee58bBU9hC"
    b"o3BHulfIJgdVL3txFzi9v88frU9SYBeaIVym76o9aLipcG5bQORHkUJ9zdUzZubZ2Gm1ZrECgaX2DsNvU1QBg4fRNQ/zu7Y7GOMy"
    b"1aj3CEueD+wUk4rR9HxbDKEYOrZydWKoTKrTN4ypFx7z8WwVZy5d8xxC2aZzPmeXnoHX1gOXmzzam0zpeMoXN1S5PvF5hExVK7yQ"
    b"l+6KtUY9OA+ojyhYXZ/d9KQQeddSdKjcurQAQUb9KVsLdT4Yv/fV/pYqXnYc09LXwzHZlqz0Y+dDdEOaTXf7JTxr9317APSTuG/P"
    b"yxUBmkCHtiwU8uuemDrH2ewESMXB0UkgaoJd1W31crBW/GJ8XGVnbFEsj6qTA/FJajEeDtRrppHIylBKtUNSO6BFYYtz4kC5WucD"
    b"OLisUrtx4+Zd7nqlHhL97Eh0p7GYuXhQISMeV9RNf+yeUXxDNkFzFphXdTUWKYaa5fzbgHGw6XsLz8qsEU+P6SGZMRbtJX2gJyx3"
    b"3vJ0jHc6xaSgI8N+gX/mOopDp/EaDlSHGz2cHpvpo4UGs8DK7UOygVVnz0N/cRcMaG3cxvdhGUqx93SYzaRgR3qzxU5rThIWNFhQ"
    b"7j7nN1Ft2cDwvJljnXEhH1hFdbblxOe6bdD3/CEiz5Ro9NYIPWvX1cOosoSR8xq54kD+iTpEzbfUbKY5yk520+F67ussEhMy+GaL"
    b"+WlxPy08uOTXPOQyJXusrAJ9Dyy1ePi6yfR8IXOis3V4vaxw1jM+w2hufRmVaWQ5fS2WcBkJy0tZjr0jSRgifOubpGyncrkwTpB1"
    b"8XE4cLn5Jymuyxf4Cluc73e5Z8eg0c6oO2pSHdwPGIgaZh9xyiVgk9ZZO9lz+rJY8VrnjamvewjYAcopix2zT7KuXptxf4heZ6pe"
    b"LqOVupwZKLsxiqRBZfa2GvvaiOf5O0ddwNe2yW0opm73wQWEyuNny3XcMFoA08foUE2NkepgqiTqCmuvB4hJLryy3ICWhQeU2JXU"
    b"JDda9Jm9zlQRK5+IPTzxuHKEso30+u16tMlocyusQ0WDGMZNuCSx3VgMHSheF1cUSF6yRG3e0c/ePJNdxeFVv/JcrZjFvAGfRlZL"
    b"IBcQg+w8Xb3UpqfmxDmGmdNhFJY8DAWN3p1nDIqDPkmt92K/l5oAAC67Qbqx3N+O9xki30fygy33GyMt22eII1BwaHvb6KJDIz/s"
    b"Nev8zro8+gtXGDu+XTC2+RFn284eYrp++ozf8uXXksHrseE6mRX0hjGl+xlfYM3w0R1pXmMlscmUle/w0utxnMsyWE7FxrjnNHr8"
    b"eCnLZ2ko1ZkpgQR6c81jx4Hidm02Z5KEr5r0UwetRlK0dqlNIT3w70XO62AV7+05KyUHONC8yXoO5u8ZEnfh/iQ77cDTxZ6/TE+d"
    b"aWZioirRtdjacSGzlkpPx/C6CfPjrHLZ2CU47OHHbhZcl8LJ071ZxVt46d4CcbsckAPhFubH4OJtNQ7ul/qwMIJX40W6Pm40bqPT"
    b"BDvMiEm2rOdb4Eu+twqhzpKFba6ejuNk10eh9I2wYvN4oiEXueqJ02dLoqwsWh3obBWKLMy7chbC/OadalroT5h9s7myDo/YyJxa"
    b"slO3FG53g6KT7lteUd7OgEO3toEubLcZuFQ9z+mzh3PObODnVuxUkpTFi0b+HmoX7mFMsFvVv9a9tlTZjrL4zG1FYEsuD/lp+e0m"
    b"BkWYWFCAs7415xF7GeyTtCJJx1pIlXXphq7GPWFiigstBZ8KwuzUsfe57vIsyEohyNQDKrNI0CMX6UQ6SwqGfQ68HBaF+O3xKB67"
    b"UhMT7jn/7bs915MVfNxueiXjJd3qM3VJ1jvuBu4Mbr5uT8JjNrX2iqN8gxg3yyuOLZzgTt06RIHc5qJbCg2DTleTr9t1WSe4kb5b"
    b"FcRU49mB5UDNbEQluTTfb7WbSEqLoe7etJOlyeOU7GP6pYRwPCQWr4JJ3MXrgtn6AeKEWDVXzMzANlC/QvjocHJT85zPT/ZL6PaC"
    b"sLodFOq9l3bQrw5or1gsJWqDfbuSu79JHZ94sYeQWeI44a/BPEflxdZ16+9Xq8DslAXqsNlW+ugU6oykOG62t3c7KknwIpOkOJGv"
    b"jTyn7yz1iDgmQSkz0fJi0MkWo6V/ok6j6abx8IyTkn8D6Qrj7WNfTXz2VOUsPiCXAXzLLPm872epUmFbXt9yG6tMLNelKzzc4URz"
    b"q43b1Y7wsvUXFn45XJTTpC1RxC57qE2NbaAqoSsOsfQkByDdOlXmBm8YI8qqxoNttd9ypfJJeBTXhoKrO2dAHWvtlTwhBWyQq3N4"
    b"Nh5ewwi8NMVe7yExfFTTyufrhLiay0wONqx0ShS7ML+PhoW7XM31EKDFt0X2Mci+cWDS6MHhBZMyi8VuMTos4Wx3ZglY5yYHzqkJ"
    b"X5ltrZq7rRrX7UUcaLTcOuyEtsGchGNLGnPdy3zS9QK4Pz9K0PCl8cUyahcTp1BJEfoVg41eLHlv53cxm7lVxC5SEkaGiI/XPqq6"
    b"E3/nIuOO+1C1QackEXmSu9zRw/oWuWbvcjocojIytoYTZAdW5ierFIIppG0K7vBWtrfoTnq0d51GOL1aq/Rh3CBzbyBdT7ERPK25"
    b"dYLgz+ipIY44r6X6SRUGkifxEttiDDjjWjdz3pelTtc8QYcn1vOP13praeVaxWplT66v1FDVe0Qh9DcvOJZTLWcr8Fehg0eNPnl5"
    b"+wNB1ZhrhfSY9q6+N4HAycu61XaN6y5r9w4OvLd71vHhtaaRPufwPnDLXttg4bHWOqRZv3mxRXcqOnqlBQzHK7XOaL0Uq5mu9LwR"
    b"oQcdoGlL0zdvLXzN1JkmLEYHf0JUcZp4GUpAsirlx3sSYOaxwbLCyfKq6e2pFh2O2ClXzN5b91r7OJmWKB6gbR5yHmxAhaOWiGVf"
    b"eDuHFMZNhaxfWntOEWrx4212B5N7ysHbUTouDujJ2t7JfUNrAWp5W8BvB5muTCxYHnsPg8gvUBtnltFtn29eq4G4gXpkrSdpOyTq"
    b"t/dWPj1Kqd6D3h57a25dMxjDefr0/HKJep+kcrJu9Noi8pSP8Uuf7M6ehYRFmepVo8FKAcaq1eSMVCGx98AuxT8vm1FHf7QKU+JY"
    b"fpSHB+h5KxLjF+dIvWw6naovFYbHkbnIrSvzfcOJusbs/g5UzOd5mnzxVzao8wSmNcDSbmBWHvdVv8xIZ+F6KZyOSi/qlRjIeAHE"
    b"5mCg3duYY3vG/EmNGK5zU9JAOdPy0RlUinopATLjk75GFMZrO+F6IdSsN7oFASxM6bSxeiCtynEmmXUJQKvFF7hqtH0lqfSIEHLu"
    b"FbSIp29kKlYj4zwrPEKjNJkHVo0tGntywbtzYCev+3l0I6eyXNbf0gDPj/ElegXWJ/btjcHATQPPEnwgsppAJFX6DOSPc0aELjog"
    b"KusBVwpTilsljWJzzjvSZlq79KCloU6g60Zp6DkL56tA0Q7wMYsWyT32wjdoEaXFhzbDhYfcGT5G3be+Wihcz7HY9u3yWBrzPVXP"
    b"5EbUDD3x+y0U4z1awhMfC7aaBmQwwgA3aFFLCIBQlapm7yvDkblkzHNs3igtXSjPU+kYpea0vRE67opYqeRosH1Li0oZf5JSr1AQ"
    b"is1zkZlujVM3Z+ncOetOzWR/NqEKz7nd++VyLyl92sVnxHLY2Jb3LnLQalCxcoXY83VWK5ZtP6fQtE7Gsxi7e10lo7vt1ar0fFTf"
    b"Trr9a6P4aU+74eQ2oSD9VuymTsF5kBDiTUtlju6wlKss0gVr5lOn8qTxLLprs6KhlQvZj7gdF54qEbeVsYGTbcB9LuPgPpqZjsl1"
    b"77AVc9wsf2feQSU78r3Ght88oEc/GmtVx33YjjIhKMDU8dUaUg8QS49k3ctx7tIcMblBtA9qcfTQr3iY3+S78G7zJJB6ZPn9zl2g"
    b"58/KXCmuCTiI5jXldhejdwRVdzfl8CIHL0wUiOk6NxX6c0ZZLrvNyFFkFuSVibBB6kMU3LcEIPa0wokV62KmmOndFq0+sTvqtcJ9"
    b"2LjUJzm9tIPgCBZqJD86Avn66HrhFuDy7ZFekHm8v0yuN65ZgNheyeMnrZyRgrb51mjXzHK6D7fyUiV3OkmHnDLTz6y501ZGWtR6"
    b"rze/NAf7vGjlc1FjmuqBLPiYwvEiJG9pTW67QozPfGX4NlCNB9MvhYq9iZnDyhEHZHVjjsNF6wz1Ct6mBVb7EtqSxbjq5M9Nut24"
    b"dCUBqK5JYoQOqtbClchSvsDB23tsHjb7OuLYpcBe9LtOlKHmj1x3koHf7qw4GspV/w4uR2sFlCR3xBGz6BJflJKlIFYktEQhKR4L"
    b"gz17xstW2l7sxeGSxqqG6/bh2BuAHNY9XPEhzvZOzT1ZiZts+bqmTa5VbKPbHGeevHewtpNRwQL5DL1772KKPbp8uTcFtpVvnUB2"
    b"cpQHwRYX1aM69adcdoX1n1xKtx8tsbmrzmCm3TkEeocUi8BoQc/VU44YpewtvR05GBjNS6AGrJc97p2G4zxa0jls71J2IRORUcWY"
    b"RrPZpD+3m26juE8z89CZ8wKcb9FjPxMc9uDzcqtT3qpmstq6Mqix+rzc44q0qD7Iwe5CLoqo0EJZcL6iXd6qHNNU5h2srXNz4xjn"
    b"GTMEiBpcyIxzTHYFggK8K4eVJ0fzc5m+TAy6z/JPfEMkdLE6ZWuZfdG/OvsO2T/qGj+dj7b7XtIlt81e90G88AkBjCOqsuzTy9qO"
    b"eisR4rw43XWBHmgKm01t/b6nq8I1mymXstWV1pX1dkxft9d9rtzvrFfXg3Gq7zfWZqOJdqax8xkqZA8MAnj7JUFNj52W2yRuhq5j"
    b"xGhfkUbugZtU36rxkJhAB+bpMRZXWOFOmcChrHb7ZoUuF7i+X36mg8IhKEcMVitwsfR4NpXCXEeUZTFRq+bAZofr2E9cPM2Mi3Jq"
    b"hayV51SNQxE79OqK025B1PltNeILpl2pNPyulhZOJLWAZBxH4Kwwqwtr6JlBTH6R7RHpXc0E+5ORnJgTdCrjUNHKZ+HAkl7oCkzO"
    b"szVRi8o6pLlEpXw62kCLSaGxmZRbaobfvZ0JaxzKHUp7nN6AUXa2zS7AUzmOol7dvkaP1QLsJEBqm840d2f/0aJF3oTMY/GRng39"
    b"C54Sa7cY8PIz/LiXXpI2xjV46Fby13GKrw5T2EJx4RMCvZ10UTPDeCnrnukwajKnroXt/H4oxVA3kbV+Weqtc3Lq6lmr3SZTc4Tx"
    b"hs8B6EnHrBDDx9sRZSwH6Y6VzVbhmZEC/N4JnTTmDsdZamIsqKx6djantxIhqWxUSPCjdZrtM3A8MnZYbbBYrTjJEO49fl98dICh"
    b"sK47FtcLk0Y95VbHnSu2nBR7XWFg+spSPK19wl3bpHIv55L5SRt6cDaPkqCSz+fHmmK+P2ARA4LCmN+83mgF7s17QbnH6AXoI9Vw"
    b"BE1TAXBbqZmOsZuEVxolmUMAa12rcSo0oxmuRXYy7k+mUhEvJ/qSyLhmdmE+vdeOa5ANVKXrStlC928O1HeRJhegDUBNwbBYE/nl"
    b"2OtGQ5ghhNpslYtn8yGKca4RA3rlrmBOUFn1Rm5Duu7dg4OTVhdjG11VLXdztx6e3MlNv1pMGvgT3I7beuqJhaDTfruJHcVytOad"
    b"i1u6e0tNleje6Dxl/FFQ/UY7WZ76ap+/n682MTH6F0FYMNaGWeuZJL85thp1/pZ9PLzSgYVOdai2U9hrqYSOh8bs2RBUMu2dn6Pn"
    b"6W2gFrNxgT6BMDIHoG7XWM/Sq0ETq5wVuKNx9LA8Wx5SQQ45++dsqV1M5wo0ZTUoBip3lHoFWt1PVbl4ES6eA/eqLQMFRkU1cvyY"
    b"4qUSya9B2j+/w5qHtH2zUiEqFgY1RVxV9I7ltyex3F1khmicY8lprjcGgknEOqRai4PJ3BXLV26XPxKzs92p2RDbKscxbRwDoV2d"
    b"Q6T+yNpGz2SRk0hheHGVSr+38MionanBChvethscUeer1jqFj2SEii8ILFSVbqwiXakwZepYhzYk2HTzeR83mhTZ2o37p3bhNgWY"
    b"lpLZ+fR6FYfba2Bf71TcuRnL0nS91rVM/R098Jl0He9yUixe/YlYagnnOU7LWlqaymuHOTj5bHDhwZ5RMF+mWaVxbScOH4Gd/rYu"
    b"s3m3vFwWokESAm1FOJf2W7xbq/aR8kZdaEWnmg1kXsg2tXfCijDIraV4xoT1TRYND7NoQIwPJZAG4825XCXYOdxYl1PW5KrWMo0T"
    b"9GjKQrimo4V6JRqbgmLXWxAvym29YqsOXdaDOaTcN87aO6eJywXvZi7qG7ObOR2M8+jOf9DG7OSSz7rfjBe38nSJX0Cycl7p69Wo"
    b"X7GCQu8JepUQE9YTgTnmwJU3zWbbo/I+m8JmtweyRhgbTe9jt6vEs1zXxfAhfNbGk9g0Pkm52O0sj5c7qt8tmFgnuadFIEsg3Qre"
    b"vDMZH/VAoTlxK1VidQCEap5psNI4KVOr7QLEz6OuH4n+ZlglmnLg61DsbOXxLE0iBsDtLI7sieyhdHhv4VE65wPmva7WAOKlj222"
    b"uV68YIXPLWuDbTHWN6eEec3bVBWz2l/D8paurKGLlss8oVrmtuihRhldpwyA6g5bIZOPT0LcE5fX2e2Uqc8iPEOyo7dDdbps3YBN"
    b"7zgcl/hEITLalu317b58Gd3ExgAvXCuWNiGsMtbm+9u574i2dihJXQy9A1be34kpv8aPabeOHDaU89DpTrwhrmyQDo+LZaVmxs8t"
    b"uHoDaQEmHh5zn9qzKKtSZ/thNK5M2+uRjDPxqgOlFGhcfomp1VVjphUZszt9wfR6dQhMZ3Z13bIsWhYSLQctYtafK+Ity8yX+0fO"
    b"qvF54jjNgB0qeEsL5LHrsB1x1CdG1KAIXrx+Wuk9tBMPuMNWN48XqipxFbAQWbLrrj6/SweOwYkc1aEf3mtRhQtecOiS6u2ldroc"
    b"dWDu6FwmA2ZXuKNuBym7xOGdyzlvhV10njwNj4JKAk3V+AY/3KKdA2yum/cXbnpUVv08zTfcgi4c2LqG9VOVytbppupirb1FytPU"
    b"a1N0BG6UaT3iZV2Xpq6tNNMIhTy5U75m08ZbNTYtaRkxzc22V161KbYo1Z2oHpSWTkty7j1TIRvzYlOv6Xg991xnMS/fnyMhwjR9"
    b"Q37sX8yy1QVBIvfTA3JbcupQblTs4lLszsaEfB2bO2CZhd4JK+dEppprDFnmZvubWtCBSWG3HpKKwIriwaZrceo5PsRhXESwQj4J"
    b"zpgyqmxz13tz+bisCmjxMNZvytFCLgB5IOeD84xtQJI7WOR3o+LdJm52rfHmwO28KgEntrqZzxutC1UElqhJVuDjLFviZxNAgJvR"
    b"pBQOm6twAGdRD9vtxsHsrl3agfKMcu08yN07wcKfn0zUfEAjansEy7PInVu1ac7WFDwWem+2yF9HHt7WnD4Qr+gC0Vj6g5LOel1p"
    b"NUkgFJfMvFk42TtUPQShsy+A2HqFzO6tmiA2B7tnZzw4GrpCH5bBwtjkjjlj0ZCpOnWpXXEXpBvjZNPpvnPOTNg/d/TquTcJoVEd"
    b"lAyxXhhBTvW+o+cKUj4y+srBFNRqe61nXSruC1yHwI5XuCFXu6ozHPfyVg0y/OszbrOzXiGEl8AiLgE5QfNTa4YSFB4efZIa63EG"
    b"9EBlu1XDuTFwa8BuHosHB01X28GA79VasdNPNWpAPT24Fw8JD66ujRwmLKeDYjl9QyaalDctaj7f5AunMxEgN3w/cubhVeFxnKys"
    b"nYnydukf4EG7pkWI0CTvM6ritDJERJMvebQKWcIZM2gdccusMyv0t2IBQfaTil323HI9Kw06bqqSaq2TvgkWkvHuBE/MwkbghxQ2"
    b"Y+BDUnf327Z3BifvOhFXAC7oYmjthnZFaww2ZKtNhDGh3lZS+brxjzuq00y0ISS4rcz+dJDraIdbF+cYg6mHi2qgdbg1jfUh/QCO"
    b"TU48SppX6I+T2uSpY01v0jYX+fFbNbLFUsbfg+wDudpuSmH3RBC0ty8dwLZIkNFEvd7lw1vdL+zGs2m4Cjhp8uxDpTHAzvR8mDwj"
    b"SGmzhnq5jsv1xDb7KQpb3XKqeX8Z8sUGag+P8+t7CwP7HOLr8C6/OB2rWK1PZoejB8aR2gY83wo5uwOwUwjeEz53OV4wtuQNoaSR"
    b"7W7BChEOCw8qU6RXI0Gk6I4NZovF4aEvqnU3QFaq0Mliqe5MfpekSPOlddanjUc3OtHFARZXoVa2u6/JyfJKM/PETBU19lTZR95L"
    b"x6yLOul2lPwUwy/AbGu2DpS+SZ8uvg2XsMK02W9aGiUby11W2HnN9GGFDwb1xtvHNO0N3GiPIGu7PrzRHVWA46MVLDtGgmjOULuZ"
    b"Z8G3D6W1LcudeWTscjB9vldr4rmCXFJcezw42Wa3gwHDF9Oay9UCqdypjrMqVmixpm/R1zbzHu+kvSY5aY0knJegEb4043Gx1LRG"
    b"GCiPmxVX9OQUzvs00TAyCIKf1tPVsSa1ajCdKXeKYQl+zKIU00SBmJkD3VTqOEZOjp855RbCea8NeQZtFbtG56fAeoEvk3o6JUob"
    b"zrLR8fglXY9hwWoOQ8y7SUS4GWWGvRyxTrVGrr6gVwfmdA+0skThuS4qHvImvOivLIkbtlepfkBKI9REVwc/VPqjoTO3F6l3EgQR"
    b"qYh/OEtGNa8cTxNuACx7TiLDi9YOTjRHU9uZyVYI7jP3kTxfCz5m8XVdBUN0rXXHV8uxXkCrXlpKjdrx0tlSraalPO+t8fM6pNbE"
    b"Y8zuOfEt2YfyKUDzYVRgZi5QPt+x626dLM6bPGUNSxy+75gl6XTFZoqZ3skIwQx6rSWJXtUVyr7gRDVoLJbaIjNYt5/Vojie9QQt"
    b"O0PKho1J59P59shPTtc3kB4lu0qtfslCPaadQ0e3nd8tttgNcDMHL+ySbiZ5P/TC1ILOG3CjdIebw15r0tU1v9fbL1jvwgNEIMlj"
    b"qYLRdlucdVlTvtqAI23J7r1V3LOFaUN+B5WGCaqzNYkkRicnPUPDdYfbrYrHBlUMC3J1evRKF/k2SroBOSTrwbZx3JrnWT88rqca"
    b"PVzvyCTA5MH8QMGVufCyHcbN8/44VOJNh+gx6X6Wnz3On6QKmapdPVr0PtLOQ0evlIsvyJKbo1EE3JSSlV9A3a0Whd2VqCF5rHY1"
    b"8dah7IMqbOxLeO8wq2IkU1WYVp5o+JPBjYD25u4KYPDoubahxjhOUhP6ra8u18phrCxyV2+/zOMTyJBHwzJld1hsOHRrzU1DfMmc"
    b"WumGIgxVhbkr0LcJbp8KM30h48e1I9PBnpl7Xu2rY3FFHZalxnhR6YVaXrHI4O7fn8M35Cw8S+21F2w2otL36fygmDKbe71+kNR2"
    b"4+jcB9hquUFLmxTatR9W9NCZe282kzrnKhspFn56pIP63Vd5GE+aRIriBXp0lDq6U24UK/Yivsq03QXea4WIYahWlUo9UUoEyp10"
    b"O+3NLnLWMzJCaSDa9fDQ5S/Ra9OJw1I0d6POE0sHh/Zy18BX5klzA86wuOZUGU8f4G6zuvd2RasuPc6nqeY5QHg9vMOa8GpTwyWq"
    b"nAyNmv0yCMCyeV8b3gq4+QfNR8Z5FKk0N+maLrH6vLoVrRzyBMDrxlrd4kCvrvNI41gojRph86KS1v0gPUbZTljVY3WGeGZj2Ibu"
    b"jU9SmSdVuw3kuVWYnQFL4B0QVC/7KZrfImRspWrSLpNiS/St3J4A0dFBMPS4sCzTGC2OZFsIFYkqtUdnb7S5KNQFshp5YUvseo+G"
    b"aRde0oUTWHWlvJ10BUKnD1QRrRylaTrXqxhkvKzC6WIe2NwPI/xQQ8aOUck1qJVfwnAuXgSvbV0uN1eD6W0S4+0aPeno7fYL0CFt"
    b"KAvppVWFwhJSTl/x7CxuoZnLO9rNLfYkgvKy0a3zS6s17G2XJRsCB7Tv5CuzLe/d+inxhegy4LZqVio5uU/qkmQC2XO6okINdrRg"
    b"zR6/agaoTM7y4iIlhZK/Z8Yw362u/AY93XjDt3nApe4vFJS3iGYj9dinWlUhn5zTd4OSnSEZkukpnKk1a0z5UD83CPil1uZK6Zyx"
    b"s3hr5doneCv6zbGKxNZ2hW0u6DZXWRuByRv90Xbpgr0+Oxq8mX1Qze4ogqx3zYF4C9MlqCvJyrgsilfYy/FxHxSfGbpR6jQ3OY20"
    b"hXt2ymvpsdjEg22dPpuUOJ8e0rl2o0nX/WovTbp9Vc66m4Xv02awJ3qYXngrkQgaP5kgBarxXEKyrggHRJR06nCtRHTsaVsRvQNk"
    b"E2GhBu1vpyLDJjn5afR9c32PZTak1SQHFM3nVR+wexAeNfqXZwqLT8SkORDQ5S00t3z9HT0IZgvf6hP9chTEnLCYi5dap3G27qmL"
    b"bQ3YAZw2mYzOiumta4nHw6JmIPrU32a0Ll1KzpiUJZHWwa11e+AJ35ndpLSFB9li5Xo45a1+1ihnesvbu04E3gB5PB/mAXpb8Sy+"
    b"0e8p51p/2GpFk+QA5g/EQ9q1Q2WCQdmNcpgdm9B4HY0X+awVh5crWbrp3Zzl9Sb7SgbNHOXrDYiIqjkFJlCGFo3tos8P3swuPyeO"
    b"WUL7hzKR72I49BTCVG90DD3VaqbHKFqDe5v7dtMclzcvFNDEdoZ3vNLPbMBM+jRlLPmUNZhqk1M9YhatM1wfCpUOsXTcw/x6NW6Y"
    b"arZL/Dvz213G3kQaC558XXUafoFd7zh1ti00BeZUM+EDsotKV0RY1UeAJzbWymmtZFZrWNv2LTYCLjFjkcwMTD3NMIuMxy2AgTZ3"
    b"/rrTnxGtoW1zcMq9tTBSKIMvbgk8T1rzrXikVGYJeOv0VkXoZVJ0aqhLuJvrk5uMVmljl/R0euBZQRWDlRpDOXBvsW9KLTeJtYdy"
    b"SLTKhNweNAe1ly5QuGbh7G01nL/zmGpJ1m8Ho2V7ZUr+Fd4OW32oNSOfHfKRuQT6dCi/HlFzbL0oEfdF4tql4mrYC4vAFWpNB22q"
    b"JCxMtoZD64m5f0LI7sArGMIy62evrO21wh4879S3YErD+VvD2vbumr96zPZMnxbpRcSP2B45wNBWM5s9Bv4s35Eh2I4ehQxT9jqw"
    b"DmCkpunKGh61o/x1i/nUS2KdLTUHtwWiKmQz4/aO76EbaZyS3s4E4DK1+8fJqfKsVbNmTImTeiFYxMioH/Zmu+KAWGcBc9olMsNp"
    b"uWc2TjrVawXcRl/q7bEClK643HrWBgHeGZjt3YbM9vbzQ3Vo6LNqU7AGaOUilt4lKTemXsmqUtPRxeyzr4OX2xiYxUfzyMzlNBzW"
    b"77V5oo/DvMjv6f4cV9JAOG7U3O6AUm+I7SDl5nCRK+43kChcqVUDdcN9cSouwgwWkO2oMbhA+bc7i5bX05vSk2n4Eg7Gs9qOQ8uU"
    b"ZwQJoXVXaRFYeJnzcWcYhX26Jzp3z00LTSGeEmr7Jof0sEvFJXO3isfXjXGdRFwxf/RGtlwHGdA8KLPhjRKN0tv5XTvb1z5AS9WJ"
    b"oQWj/mpQPKfQs9rC70wJrPIBfRlxmdHI6FaRhi06+HUhG5VU3gg1RAiA+bFmNNrVqtJcCymiEaVGZn6rWGIL1BebfTllciPjrUTs"
    b"BVSIU6Ls961GgC0Znu/DanVDS57k5LS52u3v4Hb6sWHU5ik7uXeRrVvqOwaoqH7uUmWmqrtyNB5cnu5sd8bIlPmUaMjjxC6YStJo"
    b"W4rd9Nu+Esul9R28XClpr3bT8/78cGl2boHaugZZur+I78a4mYXO5Jw+JXnROUYVNYPUwV7KvZ115wCqI7Upb7I580aRvdFhPj4+"
    b"7AkDE8UXx+rkPOWlmu+4cKYHCaOUfHr43BykcxQz687QoD+Njsp+n+cnp+yJhuHb4ETcePdlOuql4QGXvSlfIXNKW+91mX3upNYb"
    b"ITo/tVrtF/PIsnlYbvJQiltYo06tBx8/SSlnjuLa/oNJX3WPUMbCdZddNEl0cBMa6H5cp7IhNJTsa2IukxK4WvtWfTc8tHplq8oh"
    b"uy28zPYyo5etXTHau3Y1E7UO3XusDUuH1UC6ABi+E7DxO7DeqgzTCqXLz05vs2VivdWj+Kf2LJaCtD0vF6xdIQjp0nxMAQC4ZZcs"
    b"1n2c8TXPrfFuqyzU+5VCoVk92Qik5/vy7dDOLvvaBIB7h4vZTqX6nkq+ze609f/ydO3L57pd9FoMmWKa6SRMqaRSiJzjDxUVJRGd"
    b"CNf+fn4zr+8NSDx777X2Xms/YRk5Um2PBahF3J21y3dEKVp3HwIbouq99oMx1Pwm30Td7uAR5rHKisfFt39DJQqy5uUw7ffuTzp1"
    b"8dnhZCKQa82P9eC2qzyIi1BqtB808pt2c28HKj/X826/fBpcKFEnkpqlMY80yGzLblfL2faqral2++DPPaeYJ5k1GRj6cZuZ5MvZ"
    b"ZYIMPndtLx5Avfg+UXy9PSqeY0zGzivAu+2S5wn7hXCaUHwm2xVlC9/5fPf0O3HB+novc2CW9UcZf+Rre8Detzfcpzbn/aZ4nk2F"
    b"0YwrlS8CTD42XHPnrZQ1xdlBi03nuKRywIRlyQJrqsCF40bFbyayH7zh5zPPNw3mWYiL5XWo9HFi09eNrPkRO3H3XNUV+g+aCINO"
    b"Kuqt+V7n7jQZEXUhqwMylLazeuDDhfp6DbeEm7wHALPLrhTODYd8cNmMO6XfCZzt+hVM1P6YB5YF02WpAY03t+rpQsE39bMaVG7+"
    b"LnwdG+4mXOfzXKgBr+P268muXis+cHNZvRKkc+Gvgl/Zc7WmGXntCFiv8FqdjKzgenZ7K/unJi7XqU7nun6QOwcap5gVT5OFV+aY"
    b"MXAbAf3BiNbiUV5pGKlep/RyvTF8UXZvJetEh6o10fPuMtK3JKcm8rebX7Ehl9TbrcLhTp+M1Lrotugy08Ov4A+cdI5YeemGau3i"
    b"y79P7GE0Mjv9LQdNltaIBle7t+6GucEky5QGJKR853srs40X2B2+Vk8M7rX6Sz+SKaXOgPUlbjRmxe5TJ5GxVdPN8sT9tYlZOqCl"
    b"7hZJ5m1dE2Om866+p5+vmiv4i9tgWMv4OPN9j1EKN3y4L2vIRfTj/BEnQLkZQUG1Pqkb9z5ykKJxzblfVUJggyXotP3BobrYWehk"
    b"/Vz8YyJpvCs4eFBy8CPtgnh5OztN8KcP1JhwK/PWm+5XYKfW6MbK1CzXy1nlkgdtUqTxG1c49B/c3qOPzJC3Tti9ysACKWbxREVi"
    b"JhdgXH1gZPSzOUCR0Plesftm3dwBUiaD3czsq0spUrvKtNliCGXh3zq7iN00YWFbSm06kGMUbn7mzaeIi+ECHAfrI0LR0wy6m2/H"
    b"14q9dBuZ9WPAUoU5NWnvR+WaOEQ3vGzDtxCSwZaysybiTNWwUt4UtcL0av19ZxXb4UHenJbgHMiJtAsd15P2YcA4qcFFu0eFkxMn"
    b"mESvfAdg18Obbrrx3quW2aA8MmW8hv76gZf5CgevKXeo7/vcQmwNKsfhYmkPVeU5anZL2z+oRuX8TG5vHl370qSLlwHD/ZVQl0/N"
    b"ej9d+qUlPVxFp5OoXBbqUG9JLeGWCXQNNpgN3i3RwM97cFuz+HIFkkRJ1IBN8EAlP01sRTqcWvpqexzFdwSIvvdFqhFnLYVcu/sC"
    b"7QifyKNko128G1gsK7BAPN+gXSz3w9f+APqLOjat+hMABz+BmbzdX5/dgA+wua9KYZjl16/pL5w4VaAHOQmT9z5XbuyYuX7nu4Zp"
    b"jXBAdc0Nfd/Ntmgjz5LZGfOrknCO649lczMx5Xb7SspNMT/A7geGNrDluLf7+9fOah0xTKw/JqHA52A62uWkGM2RILS5qyQu4dqc"
    b"lNMR+n1as79HGStWPbUGGydFDk/ch0kLu894XhqJ3ZbffQnZfSO8Snn7KHNh3rD49pWDhM/jX5dzV7qm391u70Eui6H0iRDOWXyC"
    b"2pN09ej4cnWZ3LJBoz2qrja+SpMkVCoxXRcYLoQ2tUILcYJAeYkS4Cl6XjClB7qGtE7IjV+s6S252+b6+omLVrexsb+3h0alpN3Y"
    b"Srtq1AODp0LuPgDnMABf9/d5VqBS9jJKiZ9dQGJ289p3IVsGr+J7eCJwaho64gXIXbmEyZX3kaA3dhaSHgOPXbXsveWft7vEkWlz"
    b"XO+/v2X07k3vSELvsVbFlYT6KAXss0Ozs6pSd+yHidMyU+KMNVD2mgNU8c+zPYK7jQyY1Ep9AHkK7WBWYTb1JrVpLh9fejziFts2"
    b"xdv/1Fk1lMzZ8q4zunPL7gS3RaoAb4NhvbugB/ut05muvCuLQsmc3BgpIA0FLoiQcuCd0RO/up/9e3l1fjcBm2td8KezQb4qefff"
    b"f4lE0Dal82pg/kiP8jxouBjb+f5ST2DWxcDnROJgpnWjvDLTuU9VdU+9jHpNXbTkZbEyutDU+6KtTQ+tM5/JmjzgeZ0h601jc7Ne"
    b"W3hYGeePgZ87o+3XrFZeuViU/i1zUZxO41uZxfSjGa/AQUnzk1NryEzIPqWRQWNzoENcDnvK9uosFtzi4K5WoLf2kMljYava9nn+"
    b"8NrsK8RiUL2MjNmx0554Ug0lDo16vk1SM4R/egs7O0riRtMruco65nNgiTc3uD9VozrDW8rFuX2bQdzmjAVSXiYOgTm1qd4dclx/"
    b"U2bBa3ETBQ7sVzM60K/hgG3mMwrqoLZxsOLI2Rnoqpn8ZKPXfev1Cv4+Z8dJwUmQe1U7aREdSby11xOlbkC1OYMDy9BtfnEAAZ5L"
    b"2uX9tra9fCYcQDtMPsBycWTsBn9AdvymkXevdDwVsur5vWvvDlfW3PlXGvn6IqZ1fZdetF44LHfbfLmkTtJSjx+dPkkHHascVcsu"
    b"C/nvCcfq7clZ9+FlZcP+MFdI6HimwuaeIKIs62cq39qeM0sOwimzXzW0+QIZX+yR8oOc2OCyFFlkVQTouajVYG/Qx44P/3vk6k+s"
    b"jmjp6LbpBrIAUVqbOM6FZAWelE2vpeSnvgIB6NQpLr4GERe532suIakS5k8GwtuxlR+vQlXQX5UfYtL2VJMEMDhxQ6/bGG62+l+u"
    b"qS7fumHNetX5rOxKcP38OYB3GXGoxhr5HDTl7ri15/5TaT+1Fmr48joius1qPDlyXeJDklcG41n+8BQIYnCcjjf/FlrR3EzqPOSY"
    b"v5Sq1dYT2X+mPjEab9hzzYRZ7VZpHfF2Ma/AhVdcbt8T2UWC2SZC5XO6hY+W0KXUXX+VyP0kocHKoVb9KPjpeq4iaK1JxRF5+TF8"
    b"cbLiabdHg+exD2NebRqHt4H2LNvxvIcVVnsRLcbnz+gvOdiIUno+cAKFFrRD9XLwq0/ar7JbX+03o05DHfcusdzvuEe1xd6WxcZ9"
    b"8N0DQkylX2m8WdPxIO3SKDaueefw0u2uJne7+fYeM+5mpil0qPTvURNg+dFZ1lQuj2Dl+7KJrew/EcPmK5HBlHt3t8YPd8LU33VX"
    b"zf1Ulkeb8bieHgwXykq/xNTzrqPaWvw6y3oDaI66MmJhVO3xem9Q4XGSikckhE53q7R7OtsJxUyfOsxT5gVsekP6p32NtmVNl+qd"
    b"1mKq6sPaSh2ozTHwIfxXfyPBT+5brH/g7PXOxOlR3I7u1NFcWCZ0opb9avuiWOa9likVeEVUX1HDXGxvq0bwB4q6aggO1IX3nJCV"
    b"wgSueOA8pdXllqBid2BXiLgPWvRkynAIW+YRoBr3fjlwKd7PGDyI37WK+zm3AngNngXCeU7D1RtGHuBVuPAvbKn8kaIV2U2g2cQt"
    b"sRKhJU2WjNynkD6CVeQJS+kDTpnkTW3JE1k0HXqkWMGcltHcl3+WlACigXne6gH0eXJA14NqpPbjJ9mak5MS4y9O5Qqsj46fRklR"
    b"PEFjIPImkO49mWrrJzvDmCANhzReomzoarxYyuzituOGfzHBThelnXgs49ca+5t215p7HitJelh2dg10l7/c3v0j7o/KtVaPFma5"
    b"uxYvF/pk2KhnB0jIoKt0Cu5aBRs9R9Z21MAdCM4Co+z2e4jTYUa4dY2JQGsmXI/Z0tvZ7vbDFhJc2szb9dF6qqRxZ4iLW28UNqQd"
    b"oq9vI7dBqMhd29lLqiyE2day1GZafxmq8XBb5SeKTNvDl1N6P6/jtDYer9axB++cyeUPAL47dzTsrKVAG/9mjQfqnnm72fx2zutG"
    b"aXKyKbq2OSUGrJX3q2WzearTvrNeSkRImSMFr26CeRKzzBSztUWZ33f4WqlWYG2vVDNOlw7oMUtltIHwC7jphLUga8GjwW9Uxola"
    b"6zwdhmOV16/mZHC2QmbdfS3Y89T93LExKQO93Mu6jfPJq8yhO7iMmheuvI7Fjdve2ZLfbJXgTpiRSVbaBCTaLne5nrbclyMEscGa"
    b"dD7pP8g5xu1uekpPAQnsprbkMGrtcPOMU3twZ/i+Up1VEVJ7svJyf+F0ApzLszHZjUv6kLsg9bPRosCl52aVZPsWM+BseKYx/SLN"
    b"Ky7Ue0TaKRbQGvw1v+GFNK/XQ/E8KNmvuwIY9DOM0GlpF07sQbLaf8nxpZH81SToOJLt+PJ+i1bfHezP2qUWc7WgT5gWcB/XZ9rz"
    b"TFydNt0Ynp/Y52x9Rao0zHtMZfjrxvglonVc9ki6USbHPYk4qiZObYMyyCcjyF7uyYKbhzddjDZ6NlCQ6GEEB62CdYCTG4SARsyX"
    b"nfAKTBc31RS9VOofZW/TFdgmks/LYAQMUqD0i6t8daSA5iQ29lFDIxQhgtE/mnmPgspi0NwU/iEOG/VxZUdzQPrYle5h+68OX05/"
    b"mYg/6Qprbi5WMD4rdtWlN0+zY2v8cv22HmKNfzVGsvkY4+efo+KgN8UGm1fGrpwn7jxjzvvKLv0orYwJaXBT18vnk1uxc9oU6mDn"
    b"6XSP78HRECdnlwj1pFeU8aJurTbEpbzcIHe5ZulnEeLz25X1/8q617lx+C+EN50tegT6p0ZZGqmO6bat2t5s2/0qpi5cMshsfQ5q"
    b"hIk+FvW+u0ux81+Sk0aYlD0Sqj6m3e6sc06QBpM9v9tvcozj3ZTmX20FUkf9oLRPZoPop2enpGO5bRMV4jhM6RaflUsyNYcjcxAt"
    b"Vh+mJacQsQvnt5GFYFY0vORNaXoyleAcYNa0PRW+/y3mm/ZHTZ6Y9VSoCUm9zEtgCfzi63ODGbJpmfV+Bf/Ux82GFjHt4AVPS7PK"
    b"G1t24dbkceee4A45BnZt37fQv+xT7i8mnUfPkPLN+r4v9e72cZF3XcXGSbaSnSO+Fo57p8FMORgVrVUrOfYoY8d8+fLrSCsTv50e"
    b"DjMQjohyIHBH6bSujQ2HIPwR+mKIJfMpG4hzSzrx/g8Vlm4MjQByscZfpw5uDCbweDOK1ffwuDuN6udtowtOSu1SFYcexetzWfd8"
    b"JPvJRvUaKQ54tFweGji/BaOBuqrFBus5DzY6WKtpb0wc75e/CLlpiPr6tgdWZxbK2frWwgNgV2WcW388Ww2Dqtg/TRsLgFq3yydu"
    b"YXPK/ZIT+eZI/NtvccVpqHucrlbw2LnfVFRZeAR/Pmgo/snvFyiVJf3inkolpBbFV7N8lZvny91XQKJVzJ11m6u2x8uNW7/P3IJr"
    b"1fl0mPr6JoCal7b4QaPXTuDN31yYrlhZuNvB+3ScV86eI+AnH91XpMEyPC2HiDc6fxSEXWCSepIEvhE+ZPzYbrHT4o/kzrIOKgfH"
    b"6GW6JP2Wj3TP8jurs/I+HPZJ2NX86csnHt9fXC2GhuRW+Ie3FJgrV24NlxlTPwxSY/NQqfiFhpqyhUz1Y0odqF/3ardmuTGqImro"
    b"VP4+S29XsJK9sAdqLx83Dyy3mz0pXEvb92/3iNaOq1ZtQ/xsDnkJjC6qAo/NJ7CeQ/1Wn8v7tye8pZrFvfCmphs9P48L+sKO6nNH"
    b"+PW+wijjzyFY5DeWHx+gcbOZlbkXFgzrS3DyMbq1ZmN7i1pIvDI9G8vWxa9eUeGiaBiymu07b/wxnhrwNl0ju/PJDFRSTQGl9bp0"
    b"VPw6gMDaOB/X2/F8387D/ql03s/dxuK574fBY1pZ9e6XemXoz8WiPuHVNide/OiuLvMP8zOGwq1Dh3tsCwlAnPlADo1Ah5EMytah"
    b"MjlvNtcG+K2z9npa0S1a79Ue7DqeU0egTVdfpQP2rI68qr1qLzpSmKhlMqlVqeb2e5MXxmbmlPudAOfXv/9qut1IXXkihH30kNhV"
    b"XvzEnk9O3jbPyv3l5vFhVMlBG32iN9d84hMKw2CM7sgm1hmNuStHNWSVPQpII3/ras1tmr1XH4JFpnt7V9XXaNuC3eCXLYbmE14c"
    b"R94NlKdB2rw4fOJdrFDfBodbMayflo/FJBp0jYyiqfmsv/3UFosZPu7c+3/vMsN29oOuk6i/PJe7QH/Qso+N4WqGDxgac9EcY4CT"
    b"2vq91RB7Vaxd0qKFRm/V6wY9N4LPinM/Xi4BoyAqGE6XcEV9SS/1eVl3Dq2bxr8x0RL2Yqupn5hZY/bk4quVrM+Ltm0S7XNuw5cZ"
    b"XT2eJ7t+7H9mpR+6lcThe4nnUhBd56J/6E9azI6iNtE2usNlbXVt14BjD7fYXgOdXWCrt3Kox8lapC2zA8zk5yPHeABjDsZHSvYz"
    b"v9utE3IyVl4ZPabL4bdzF96Ln921ekN1ylv6Xtnnl3dAuPwldVoHvqtM2OSnlXHBNb3Z6IRBa5xs/LXemMrMmKrjJFcX8mm1+dwp"
    b"wjvW3mJvGCr7v2Naax+sgynepunt8snSY4P9/v9R/d3EECzuc5y0lBfWY4vpB8F6eG+y6l6CS5082OOWgj0yo5YfPsNiyx8gYRP0"
    b"PJK/sOxUSx+TBdjhVjryvqMH6cMsb7Czv467f8cPAQA6Xr+yHzhbk/YSxkBTm0DovUch3/HXZ8dVuV+sLzkabQ0IZr1EaM4XpdGl"
    b"pCPl/iqDnWHR7yJAKweHb8t+rdX1aRSsh1H1up5mb5o9HbsW6AYHe7hgluOfCKLwO5LS/ip1v0mJPK/3xp/hcDKPZHBV2fp9+NAJ"
    b"iWO1obT7c/zLlnDbqEQ2bdKsMc7Kk8lRJJe6nLNN/z2L4YDqvey30NXqt4RGzlrqDoN4+q/gZ0N4W/G6hNUiOa1RnL6EzpX7UNA5"
    b"uOWWaVyv9LzTe5+PlZqY7Ji1uWBmtx6DqJXXQxCuFcsftYcrquJAAINKUYiOerNhpMVzxgyLR2ji2unX0r9MexeHZO8FQH8m7BOo"
    b"p6x0OVY61vRe9cbb6U5Z7e72vQg3Yjcf8IPgVO08ntbRkqJZJXvQJO3SCtgerKQultadTl4BR3rvGWnqdrObI3NBDX4/IJS7ZFjp"
    b"PDe35NHxIP17+tIF2msA2a34YOx7Pmmg304owMPd2A+s8628H9y9++WFlRV7D7eP46hq6vnHt8FXgyVH9z5I1pgSJ1T2AgcjEusC"
    b"9K9JV/8SpW2qOF0ZKO0LjvoyJWA4kTov7Lsgiu4I8qZv7gVQ/fo+2XbqK2t33rLwg/22tDy35iV2Zp0KO70p9DEd+54LUFSV8M1p"
    b"sEiPQwZbtJY/y7+ah0Geg7l9vRb1s1So3jxoB3H3PZgMjDF8PezZ4KHAaqJWuHraH8O+hqC9DVuyl9Zi1OIRpAn395t03+fSFps1"
    b"HXQzD4SGsMzKq/rR2MTvxo9fgafFcwTNK29ovFsXnVtSC1ZKpzI5TqUH8hb76+hmyVp1dLKPahkNK1MjnUFEX7sekQavnNhdL2jL"
    b"h2nyxyH0ndhPbeS9nA+n/eR4s9ZNl7vjy1+Pia0AIJm3+/WWVGtVWmIjtWYozZRdvL8L38iaDd2IdixUf7fBdB4Y2WMu8e7UMaDD"
    b"qnEb9A1wRTVnyzkrRgdsVG5LllXaB/dVE5wan89UxA/jX7062nL2xqAZzyzzYfsRAa8vsu8zNXHQ8Md86fn6GAfcqJIWKQmFQGjg"
    b"gWog1nFJxYvm3Hy1d1cVkm4PEIevI4q8JC32vDg/p3KJar23fdb+oL2fhbJWNe6+LU/JqiVhaWdOk9x826pT6iD69piuLKAhdL1d"
    b"lOfMRAikVC8dd/Iqpx7V/gqctMiyqOySaqPjN+0tU8csccGJpVTweik10lVITIYR9htrKoFroqW/bwwkm7QynYnQtqqa7LBlEGnP"
    b"GWGV1lcQj5dWqX8OvrDN8XpII4ejuakNspJYravHHTrF3cVyvKII/Psw3phdexZtvlQ8hhXl0IxbPxwo3sXhYd0vAFe6XGSKnAyC"
    b"3GntVic1i9/nTMAhGZrAfVMbKZ094Xr3rMa93SfG5S0K7VZ5O29bVqv3/kpz+AEp/WtSy+ve64/DjWbb7DEjVfRH5XazaNyo+5/3"
    b"guyGzxKiFcw3WEieDN7RTbur0j2wBgqYpmtfMHnMap1dPVJrn5oMRAnRkrZjdO7cPTBcCb3WVslkt5JsLovaUAPWW2kMYvOr8JPO"
    b"U5RpBsi+i8HiZnd+2c3zjN4Rz/hbzSH42Qar2zsOp+K6/jkBh8Z2cxzQ4qPmzAw6bK6nHtxejEDQDyZ5iRzH/GpaPhsSud1SqMt0"
    b"rYGliFf1pyLh7wUrx9XWBRdyMTsbMTaMqK4wo+I0EsNWUbP6ZnQpZ395qtqpvK+Aw2rzQGsxz9d3gPWvSwZOlt0/crwcnoGX4h5l"
    b"abYbtP8IjCXOyNt1Rfu/5ncLPcod+mCvZi+DC8u01EjExyMcr7hXg2s1xtyd7eokMbgm2fpzSx9vAqjdbteErZ2Lybptd68fFTiA"
    b"93fUdghdjGm7xZEdVgxXdYgFutp72/znqAiYSVuf+5fBAZfP2Ha7lCtQ4jtXbvIdNYbd+jtImaZytUxRfq3Fqf1htTN/O0QD6oN5"
    b"51OaC678mjPJYkcupTzRLFE6QanaPwVGrzoKj9r1F1fz6uCLObR8kW8W5Ns33pqUHTd3/WalNak2LEqcyuhSnh2TLXYtunJ5jCon"
    b"3hLd6u7YHFOiFJ/A43csAs8PJTT0UIdgRaIkM87IsBaPjWqV/Unn5xPpMV95BSMtKoz/6cLHxrH8el8G7CMFXwY41FWZac919r2Z"
    b"qmO/27dwtvmgDzqqC0DpQiM8FM4uf+S9KlGPrQUbG2u+kE6qGtc8IC2rb6P7c5V1U67eW+eLbutULOG6xW1c7YqeJnVzPjdVNejm"
    b"I62HM/EfI/HRev/adXcyvXqs97UG+QheDXy1utzM6vrISseCaVROb3yGbQdEal4OT+RLKxvw50Fll8zl1XvjldqrPRlFS65SrLia"
    b"cUCuoN+a7svdlenOT8LufkB7/pNfeEO1HCrBHBNnV/Srp015QAL1Dl+mq6pd6NWHP+g0gq6+tDnDT3rTtTH5za8sItyO53Qaa9F0"
    b"tX+52LskTMa0Mm1KdWY/qXVH7Ky16a2WCg1sx9PaERrFZCqzgmrU1XpCRWOcHtLHsxgxf5Wn5sYP75ASW6OrlCOFLamHzvHXJjY6"
    b"jxbUNH0Rqppg++mMSXuSZN/wIqBbbHy464HUDclQWoANUYA2lxKEfp7HxnlGfbeTXutMuM4Y7eX787CCzSb2p2NYR3OCTAkYPuDN"
    b"N35srX4wJsSxtMK+2rN8E7/MW2Rx1p3o29KrJC9DgUmzupR5ULVuUT0Wm5Un+ef6sidcf1rv70bvO6M+uv74+nr0993kjyyVw6VF"
    b"eUAVjZrrVePhnaxb47e5qBPI2TbGbrvjyjpY0vWBZmxzQnOyZsASS/I1zpn8wYwiqunVdLYMKfjxYIkMBQJ1ypb20cwLm7slmXbU"
    b"W2q60uaCUmTLqk2JPnmNwro56n1/wmVx8ZepXoKATjJ/LCJjV61OXexATcEdHY46uxJyq8hjb3kMv0FycNv3h+eytDCnzgeabysR"
    b"g34yPstBaFQlgjm7SbdW2jhMq2z/OduemuN6IP7iyqTgP85xwcdWp7u/jWcZPxSNpyGCy1MYaXDMyKUoIA8v9ty/6deda6BBjbv3"
    b"m9mQCeAxKbkbNMXw5jRtwEpSlN9ihq6svlffKGF1XP/Dg/vObz1Di/x08LKGBbn9lyQHuKyNhUupu8omPHx8+dqiuHShFmbDcFZr"
    b"X3ZZ/lz186iJxFLroGP7k9M2jenr1D5+b5PDcXliiHdrYd+6x87i3sxb2l5AfiKIk0Si9FqxiavXVDxsLO2j8kgJPHfSpqHaYky3"
    b"brNj4WO1zrzkdXxxAczup0Uk5a2HfqMWfcf59rbPahke8+1bfFWU88ZwzYOn89d94SYw5lq/affVtKAy0ap+AqT0av9BT7A2Kc+E"
    b"BdkCOW+xFkhAfHWns1a8MxvX+BLX4BX9rQD4HTsL9ROX1GOwR6N1lI+uUOl8+t5nU601o1Fma2+GnMQ0wNlv0jPl0SnyeJzhrXoC"
    b"9sNaf/CZnqTFBu9RpYGozsj/1tcjHaHUYPX+bKLN1+easO3HXs12pZ4PAOpqxS+Ej7iroNv2g4uq0nIwAN/NBqtxMQk3TvbPL4xZ"
    b"xGq/94lrfd2T96HlCZCwc31gKfun9iYTt9r99l5XWKKivzPQySBP+MrZaSxF87QyIte7UDWHyxGzmaXKYHWTNfc6d54Vq5GckNk4"
    b"OseXf27NabpY1Vm3v2TtPrL9zJnKXuZWys0Ktyx39WeHL9x0v7XGES+VtVrfVCrPpAXP7FNHbC22dcJUbuP7gEPzA3qO9ZYRN/d+"
    b"wyGWnbk/4orq9rIzfqyxTMKzcqfsrKOulgjqnEITRrSLUKmTZPae4fYJhL7aPq0sc2oL9WfKuGMwZ2vmNg4UeIFf8IpqSEWADmzv"
    b"ykSPUa9M8Z/4e0xyZY0L+zg5LX9UblH3Z/gcXNqL0l0trUZHXv62K+nQ1nd48OKqkx5zobNp6E3bbr8YDUKVujSLb7pwDzc7MaXa"
    b"mZUvQ2Xe2i3fhJ6yDQF0490nnNjNnYZ88yky/70Vk+SWOZybJ0e6i7xTr/YOpxIPZnPP3B+6SCtC4JnfI2/mIlEhx1t2MMBeCNfi"
    b"wQa6NGRPfoA+pPfj9jl5Q7MLuTuLD+qsFzCPQcscZs9cHvxGZau8tGBW0KbkXIrxOvirqe6U6O2q9t7vC1VJ5AdWTd/IlfVUl0E0"
    b"oYFaKkyq63tBFlqKZPtzi89e+xAaaN/w3Bw/vTv3+gaqDhx0Glwfamn7370HZ7AzZObbLTPdi8PmxN9Rn1TAZ/2KOvSmrWiF7Tr4"
    b"lZ3x6R+z3x3rO1JDd/I2XvdXM6gzWvT3CbtcllMKfxqn1VslbzILbJdhI9Zv+91Sz1+E9AvhRiqaBpvr5SDc8Y2AgoZzZgpsi/kJ"
    b"Xr1mvDZ6+sA97u0TmpI6MKO81CyHSsK64fSJSv1wPo0fC6GKvB20hsI1K7OfaqbE6ADHfJrTI+70hf6hWw1TI2uv4bdsNwNPkxHO"
    b"wTVR6eC11fL6yUDws8etWufIJSWt5tHS5xy+1oo1jPjEaZdI6PkEKQCuHbmne8l7awxT4wjDriFmQAYUvZufx+5nd0VH1Kl9uQ2q"
    b"I71vjzigRN7KeIGHvcohhyT3jBPXhnKa1HCjssNrw4Sw+UaKcPPXdPLt3lNps0RX3PpSZkFjdG7EDRBimbViaCXydGh0cmzCrf4N"
    b"a/ufy27+gUpZ7Q1MmrxNDceb5+Katf+Y4KikMs17hE8KoZqIb01AUD2eFvcP8twcmKZGFcseYTwPp3NlY0wEpqPfIS/ZlrtPPpLN"
    b"zyZ54+8t/rN6+ZV84M3g2Xi1y/WhLr+q+h+IQM/vIWNtxUi7BzTSRI7R886RKzAI2gfFfcwV+J3MImfcHVG2dijcYxUNFh2eeUuD"
    b"dN15m/uB68UbyGghgsn/Vmngx5POuV1dj1dFTk+3j1NUHW+E8WLIN7SV0M6mQ3h4+Sqrl8zNpDZwaorfS31w156DrO2OgonKs81r"
    b"L1TOUZtglW5HIXH6KSlq+RgkXs3sp/lPoSo/d+VU6p43KrTBjS7eKQZHpdrrrUV2UNWNIkhYHkMc/VILznvZXzX8mfuegJQ3kBji"
    b"tFxXx2CiRcDVej07ze7zUbjlKveKGkDHZYaNwck33j8mQtWr1rMEvD52rftNzL/E47Wq1U9l75p8H2rcQbpZtj/+O5FaNyk6dis3"
    b"AL1wyar/fpZ3CnY2KwVegGsfoCYJff+rxGkekvwFbQ1Ei0SMrLllf2ri5tK08Ffado5UZd3dL4x7tRpWyU+dnVE5FO7JPoOvexNq"
    b"dYUJvNHXPWrwmbBUk1fHCqPb8+uod+s0DJPyrKdlDziaEMWWLPQjxCeqh72DLvUflXPjqrVDvaQXZIJzNEIKN9fmlOPX6zn05ICJ"
    b"yXu5vScLZXmtLofQKSVQWGUeUdo8/51ljuAHhx00lBeC7iO83rqesbV5ObWSmDAHhyYkA1P/t6LmJrFoxK/xWCvvN0pnsEtfEc9B"
    b"89Qtw4cgzMpDA1tMGbCHJjq/2ZYXOK8vn3AgjL67Khwaa2u4qU+Pp9VjXlkf6/3AnYMnDCf3t+2s6MWZ5v3bG2Ptc3Y5ZhfA5hH6"
    b"RW2/fNh3j4rYwtdrwjFvTLVJt0Jcs7cQf5rekdpHvtKfp4MROvedJj8aVipEaIJfub4c1WDvVMaTSz1ZOxcMfStlC9ftwe8Etnoq"
    b"NRf+6nWIzbZ/WFpY02t7k23ByhIOqFfPaK/AQpAPoXnH3g+0N0POXPVCC+h4AvVlHdkbT81oDvtXnqmbz7+g9iiQJPIpVuBDHBP4"
    b"T9D52cgvJOPNfAq6d+PvLfZjnhoiQFbahBGgShq5Gaw0Z/R+lVGnZT1nf79TpdsTIQXiyMiqsX+R0BkKdb+ZBaXUXGfwvS1GAMER"
    b"dmfgNp6lGuxv1j8dE0jd5SYjbPXr1CVFudlp+XR7se+gg1s+vCvNP4gb3MZYIISp9ZC33EbZrMKSSct1GcaxyL5voha+nO835Hiq"
    b"VScCPalg1hrOR8vdH2H/VuePx2+Cejpv9sKWCm9oI5wdsZnRjVlcmAMXaE/KnSx+U+9e6/V47rbJidfa10I5XB4qPe4JHeqp3053"
    b"Sm3XQnVm6t8Ag4VsPlkYRZbEYXLfi6kDXqjWb6zZkdvAfC9j5TAbnSJq3HjdD+BRdQZh1dS4rdBiNr110cXkXml+8BC0fh5U1ArZ"
    b"0bvauh5uI+tk0TizA5hgUTk756V8v9xzuzwxDwI7OI75YXz/XfJxdUvIPA3+zpmrLsVHT8wbNvFQc/g6FSbuUNGwUrf8GLE9FkU9"
    b"HsJnu7ZNNFXT0Gq3Bo3FGRTxAHK4guOnsc2suFtqr78Ynqwe6jdSlE2V/P67hTJWZyjc3zyg6umy73BG+bvZfL6jcwVQ5dES3xvq"
    b"6KrcuqJSqa3FE7FQrENEOR1ywPQupuyJNuW+vlW4YCZscCxBSXmeLK77S9FcGqOkRcqHww9Ij90H2twONGf9mt+IU2NWedVoAL8B"
    b"irW5rRqVTjBCJN1wdftCBsuXFpgt99O2X+bA6om9b20KZJKBLFud5N2akZBUSs/vzUzE98lLz/VIKRqbf0wEGnLH+XrU2c86cHHD"
    b"a1P02qllKScdj5sranx42AGfPNV3w1u2HkriuCGTjRjrecPnfdRYeWMbBL/3EPkDdu3aKN6coobzFLtCH78osaqtxtTPlnfuub7V"
    b"Tvbkh/JXVwMTZhmHkL79xvxFE7+Ak+VuBuhJXJc2k71zMNPl1sq1VhGmTDUoX3epwkHr67Gq1XLtagjlg1Cclu/GebQP9z35M4Hp"
    b"9a/HpHs7tabQnHmt/7HAhjL+4wruRhkznbEtDqcqf9CB5ejyHH2Pi6Om4abQlvZdg2Ja1fy08WFdOkxb3pYEJhpTSmXVQl5wxWwi"
    b"h8uS3pHXNlZXf4sM6iX5tdwC5mSn3aphn4lC5DYcoc76r0KMy0QanONofnjXLWTVDSnpNghZ5BzFJg2CREbA7zbWvfOdjqG6RsUE"
    b"kv1/0+U3Qs/ytxTYXC2eVOXfABC/N+pjcVRvPvyrffj7z25xILX25dMqMO6Hblfck2duoFiDEfLiZL4bYiLV9YpJOqhzwjU1enft"
    b"3ixuRy6P4bNWkNj14mRBb2ZdDVZMGmE/SX4LGPGXTQ5bsQiADPu9OY9JA3mrZ+xh/rcls7F32QDsnMNzfXXZvxtimE3oFdF8dymC"
    b"fqzJE6z9MZXxDHncpQkRz1dqpfOcBLpsDa5TB2j543X54/1aJDv4enP83HJoWumd2hE+PvlQEXmbTqLvj7XhS8W6pfKgt3uU4Ffj"
    b"QQLgLFlTFCveX1xzfh3GW9OaVgZ9uGcBl/6jl/8xlWBJVWaSf+ZP14qrYb++hTEmF8bLPHedR/e/a3Tqbi5ngLFf1+xdmlHNhQ4v"
    b"KeuK9yDFaZWXBnEZ3oeq2p10H68G2KteXD/klgZY+gJwUN2Oi6vVHOwQQPdDB5s1r5fR5Sedz3dFZ5Oia0RszpBR1Zq3loB+G01C"
    b"6sAJvShGb/Y2OE0dc3UKOnndziO+6NHakiVw4xgDZIEWH35zoHx+ER9r/ueAPNctYX9Ffb4cAc8/QJX9dvy8zsFLEZvYFK4euNpE"
    b"XdwE3KjJO2eQgGWNWKXxrPUYOm26dgNb5y4GCIkqlY7Ubhrfq9d83FjcV1ZjuqKRIb/s9xKUkw6r+/UoTb0Ut77Awgd/QHq+06f7"
    b"7NYZHkOk2NdXy1GYxg1hjWRp8se8nVJ9Po5GUnuzxl9Qv9DfxfUJdsepVk3241ez3LNC4cZlxP41bsqQMbfkZQsfct+jgm7ee8Xr"
    b"v5a/oRIJbvfywPnMpeV3LY7JxmbkCTcJn0QTDtRfIraYoIyXrq+5sBuIOF4ldt/NPFGkKgjIkSP0OiCz2cmnUKHZiVPLS31Uaqyr"
    b"Z5qgqUUW14/5v41gSLVbuTPZrn9ihOK+I3eX7tsBWaiEI/0DHbD5ggbqxiRilACbvoXzLsXm/f6d6ct0bzjVQUVnJiWlRKgO5Fog"
    b"h9WY+u7lxfOKcyArrMlwZv3X5XzUo1paO5mgug96YSLzbfFKVu7f9fzRQdbrp5gQs8EqaS6hBwRje/ww5VKCmrUrnUg5x6nUaHe/"
    b"+DbeHdbxURsMWPEIAowdLNzt6GyB95PjV34WSo9xk+rRS/wdv1dXfX40KLny+fJHjNt/yFIFB3xWK5lSeZRWhvVuMbAuUDtGhYYh"
    b"GjbBf1F2m93FjsN9pHjRVGk4vcxOhPNMG9Dzpm9K9nMx/xFUeUqiKJcfFm25Ud7rJJMqzq3D30VvPjtEq8d93SLvlgjuR1rCagWc"
    b"zwIUXbK6f7kOpwP1zVnjR6tfNIamehL+aBHvXOUutDeHzVbI3drl3J/9upyjRFTNOAyZuej3hrtKnvXrMLLKyy0HGm65iSxuV07n"
    b"YhLfDfG94HHxvXMhhAFXd+mZ9qURSJ0MXD9aanjR4ZtwuCRLPSACqKXpXFffN5Dp8LdKo3liW674Eu2COizVo6+0/a4pvz3Cr5bP"
    b"56ItzF5u1VO72/QB3huVj1BKx+UKo4+UQQY+ibhVtLH9BWuNSdeqzDoJnm8jSiNuLkUp++jonQHy19KXe/DUGt17E84atfTrMlIv"
    b"fX+qlPvLZZY5LGWU0hM5fiONycFrLdtH8HZj6cvWvn7taWwt/dereAa9G6PMy1cjL0678tbuAiXLulX9xXzfN/XzT2SePuukV6G0"
    b"oxBg53S+5p3n65GRPj9UxWoXukrc9Pp3djNZduS6OLArf5Arz8fL7/0j2YfIqSbD7uAk2wFmmtT+Rac656lSY266Z+2MIrrg13/g"
    b"zFZrWjpG8/mq/1zcaBhtDxbAGztGNaZCkXJfnVVGTzG166tnOV9+mi+hHjuU5nD3K3xYp1dZnCFSQIV+INf3vXX/QRwJzXlfL/EL"
    b"7y1P9m75+rWJhx15eH+4FbPRCA+wBwBDF82QLCvk00pbe2W6hBl6BZ0TLXEwbHbGjQ0xeNXALlr1uuh3pc/AN0w8cqpPbDUq3Vc7"
    b"TK9fKyGjuQ4KUSXhWcH4qUj4skp4iBvnh/FASInterC6cq/dlFm8J1e3tl0AZEm4fMuBcNl5LW+Jxt3TEDntvt12shOU+lHnUwMu"
    b"bykVidQcOU2Ijl20D+W7NkgnQNlXieNvhn+RH+Oa3arsh+acXACTaLswSrNX8i1mi4vhja35a1tb5X8ZND9X9M+1Try2B+M1M/fN"
    b"Lmh2KoZ4WvUbHMVBgCVzdv/2uqhgY1hX1TGzLORw10B+DVVmYzTZrUXLqbrWhoYFTi1gwKYAeKW/Mleq38Ou8vLx6XXUJ1an8wDF"
    b"/TxmOg9gXITIu5dI4vZFNMqjocF0bB+g5+SgvapPadfkJAc8rJGE+Ylhy2ArEE+sV++uXE1ZJRhyo8pMBPUP4MPvVBaZ3ngtp0o/"
    b"oHnrEG+5Y4O/w8zg4JHfxMlexxz3HSTX03kva3zR8uUQX5dbEx8z1UubbS2eSLX+u6tsOao6HiExLwU4OIt605m8s+CdRBtLIrXe"
    b"FRVr+SPb3HoPGTxjnV5PnfSnxJcmbGlFrkuFLnj38FQJQRXVYB26FZy3m2XURJoaT3lwXk7Pffnn6Xn2/ZNQla/+cLddc+sgvLvb"
    b"GL7dKJIOX/z2Ad6oW2l0bNaeMJPVBxJUnn3uckIvohuvYUjAO+yeop7B89jvfeH4USvdm63R8XuKE23XWrPjZP5Dt73OjEI87LHZ"
    b"/aHD8bC8aXUI59KADlfMWWe1e7t2M2XUmc2oi9s3w+Zhn4xB54kjwmEMsTKz3v39qs+tzqEm1asMBk/3PG0vGIxljkbZGrxyn/gZ"
    b"Q+XW8uQPMXP9nSunzv0+HZT/eNTlxSNNbgLt5M6pl3/oLU5VjcWiHT4GQSmOUZpsTohlP18nxr15bHqrleZ/HKxFozDfPXeJsLyz"
    b"7ckhd8B+uf7r3Y7a9SGh65t9Q/58UL8yQWTf25BbC7RtEXoQ6N1g7benrZn6xHyq6V8MisvRLcmfDrtJ3M5WrbbnNuLcNCgaTsE/"
    b"IHD1omImIgqV/9GmezcZ/A77H4KxqNdarChgT/Tli/fcHkZVcwj11s7UnTLAdvHozsCD+/evVNDI7TDT3W1l81eOnwxnfXgRTF/h"
    b"uD04tcrP2VsGFLNz8QujgI9hu3J97Pbj7Ac5pzDTMHb6K1u3boz39vcryMAbmEQWc6wrbCrqlrs8Tw+jNuJicvNXRecUj5272oNe"
    b"f5qZE0TtLwpNzq2h44ywb4uKkerTGCzYPqtX8F45q0WnXxUWiFb8nqo1+Bw7xa4dWBSGiwKWRAv0D/Ou1RD6nnhZgmIpKl3nHrA9"
    b"H4WM2O4+4ll/Kgeok+lL3mCQs/l6stoiSt46ViLR14F9fYGzDT/31G+pn9P4npYXHl1J1Xo2IbaOy2rqet5tSGWwMHvz0abGbh9X"
    b"Wbi5bRTeVL4Hgs3WzmVZ64+OlXfk3h8Zu2w+9GUJ72+xVavKH+X65DDbSaBzgM2yJfyWTtyA6tKNiY/SMQR8Bh3pG5cUdsy/h4Iz"
    b"uxGEEDtehVnR03kPGLbTmFEu7Lq0K2rS3BgUevb1pcoBrWI8lTa1KV1uDAbE6Q56gw+UZdV4qby1f/3AFNql5M67nRv4wsgOOnmz"
    b"T0/3dmZnk0ue6EzFpZNue485Id+2++BCWMIy8IpWEO9GRH0P7T9ZWJ6vsOh5O57K7vhxjfQ7+5jOzOCN0jf+fflpzs79TB2NqUN7"
    b"4D6Zg6MTTZFVXbctQI1896iOmxmMLicTXpA/greFd5X6jLpbgDSy4NDIq4ugMgudqjU7OuaoFX8CzCX13hMtrNJmc5iblg0Pf5h9"
    b"O6pUNimOWVVstwuWidvFBxmCnZwu7Y1r4mqiesp7hD1xtoOjlY2mipVq9Jp50N8pqz0Y77OE225rWfD1cG/yeVFoXFHpkwoMam2l"
    b"QYT+2v2JzBvjnrCG+Ga3m3TWrFFdLtakHFGjbK5QKQRpm3m0EJqVQw/9Q8HBwwFBj/Tbc1hYDhzwKLS1dRWsIM6llvgItSkHb8E8"
    b"Pq+rYB5LaY1Pjtn73+6s9hAi6dc6Lo2Dg3tIooG91/OGUbw52n1lE66sCj2s1fkcqiLEbMoPUcueHDWZSC9aslaDgB5bu3rFqTjr"
    b"Ri8UXwaazbaVxqTykfwikvQCCMev/z9qkH7OSnJtTeVLBxjB/LXJ8ZlsvG+GbWf7eHFgeajaevtYUHHJEjvdCVXW1icEED2ezqOy"
    b"kIDeni3TPnL9lJCbHW2NdezX1jvtMpFiqLosz4DfZW/6pwuZ1byHK6HTJ9/2QO9Ix69DzEiRWtRWVbBPgMdJ8BXkBjUEwMrr/m4c"
    b"pl5IqAF46zvZ3D8cCG3vXsrrrIoi32t+OAX82epHWsVz24MV//ips+Iquu01NuBo8DqEflgd9QtC+ZgS8HgH8KphmuvJswxDAAGu"
    b"1PbqeWCeS2Exf/Vat/au3XGNazs8HCeV84phVVOslu9x14hddTWpy6d1rVqZP71ftniGZH8J36ZDSUI2MhCULmhN6h7I5y1K6qbX"
    b"1yuE1cbJJCPL/aNsQ1QH1s+auTaLylWatpkPdttM17YMK/C47X3XxnpVAEQqSgG8TG25TVz4n+F6uOmvztindZPyy1okF02xHiCE"
    b"yPIuFjz29Lin29p2k2yb3KBink5TrVM6Nl8arX1aTXGwEyJ60x4WPUoywzlWEUxYM+94Na0F696Ru+esqsY/KeJf5S5DEL6ok/ii"
    b"cy6YIO+5lW0NboBSexWOT/VFsafrIn2P0dTMnF4SeBwld5pFA7CCUf8iUswq3EB6S6vDZHi+LDq7I4w2WPxcYDOKjT7PFP936e/k"
    b"jvSLVF4Zdp8Ui9p4wwEGd9X47+ODHDZpeb0drbX+qzxYkLU7Fa/jtHHOTnAtXvNUTordb6IW3cli/9hi1150KY2rnxYocD6LZVD4"
    b"P56ubElVJQh+C4ESCEGEKLiEIoiCIKsbKA8CLqgoiiwCbt9+5z54nmdiGOjuqsyqzOrJpML+GoDRslm6cufPTO5ubOh00+/S4pZI"
    b"yvHaMoiOXTWYcNDuAJOpz5xHBv+UJ+FjcBbaApp5dfNxLjLsquDoedklPKCXmf/f1Lu9nanhdPNiFeZy30S/0U/c8v4pDx7grFTf"
    b"0GFNKKWNLjEksgM5NQV1Qlbp6ELuncJp4xm1tZrsgmihgdVhFEhC+sgrsq6br/NHZ2Mzrg4778QDG4zzfe+aK4p+idiuevnNIqm6"
    b"UPnW9HvKRvUrIjFq6SX41OSJoN8mtRk6r3dhYBiRr+LRWlUpE3ZK+9tnDEwNwe0/Q5E9Pmeh1XpyW3YcWzrM2M9lq03OavBCaPSl"
    b"ipKIzZ95I+Xle3I8z59vFtr3X0l+Z+565WsnQmMDu6WkZheMaV5BJR4MS/XTnN32PGM18bv6XlCHF30LhN4dy+txQrUq2KtudSM+"
    b"ttAbwWWf4r4pNfT5rwE4LIHLkiSLb79CbbqwJ1ru9Vy/d1a+ebX5YpFcyByp34a+htbZ1sJEiLw82Nutj01UNbNVlnIwXCTGzVN0"
    b"treh/Gzcxe7Td3Z7tuXFyv/LqY0fZmflzXqDPstc40Cm0VemwFVJfi+gwQZAvPj5CFruY3EiS5lhjUy66HPydEadHdVJHvnFYqDI"
    b"TvRe7qWxXm1Gli4trd2hJpn800sqwxB8WKH5q8b4SN1VXkLxrJ/VbzrUSsoInYxlxBloxTRqcvDHqQFtbKxt9ymUHDA+up5WtVd7"
    b"8H3p74Z6LVufobkuLqwKtp7x6Ia18jX29yfnMnmpXCoIIsi/Hj4vz0qry8XeCzAt0lmjgI/N+H6DmN30cq0VT2xwagxfzS1vqNxs"
    b"h3Vba0xfUZuOsWdqelcqgktzJlmV8dU0Un6QvvvMzlxsW5B5rDLM48Sp5dvP14hfORylpdktqVKdKr1+PEPaaQl9/uCBPHlpWKPD"
    b"098z4GL5amRbEUjWz9et4gjvL2SV62svGo6f4WuiGk+o55eH+hWBdV/KbTEeAvm6vXoi9K9MfLj1405G18N9stiui/nGBm7a90VW"
    b"1CGMn8QAXIzn2jibWOyYLVCXs+BdNqdLumRhSHXQ2s57ZptnFMwo+693+jkv3mUAQ8XleSGC+XOcchfrN13AOXIcI03UBVoc35sG"
    b"zpzbQdEjxodk1JEelcFOEranw2twc/xPZkB4L0i6yqqzBQn9tLmxWsprPGzneQ5MD3HY0M/OHd1O1TvFVOnb4T2u9Oq/t1Loj+TW"
    b"tlGqtsrMbZxJ1m27eUUVZMxr1ROBlmz+jkGVeQE+vFG9sTqDtc3g0L4iRWMw3qR2t3KoY1XxssNxS1qjuIbAqSb582B4oMY2c3H6"
    b"xx8ObOcM3oMdaAgxM7xahbzv83So4q/gJH823nCwT20gJ4PJRFg1j0ejmwuvpADDhtUgBjr+Wg4ci4yg6eawBBboEFnGLQ3x0HHu"
    b"egxAo9M8mOA/+1CwrXByjfvjDvpt+70c8Z4HG0eTLvFp3Og9knDZ2eZ4IM3zj8Ach/prarhRtTHjMbSzGKBM2cIS1xMW0I2kcKqG"
    b"+GztRRCNhXLvT+LIXlewye/S30rxbgd82m3mp8mBhRElaLBVpFcYPN+PiuZnVbxllUAr1P10MmZJhzXGjBDgh08TdZ0ddaS7NuNN"
    b"bt/Xbun5o3vR/DLgeMXRnnkIHjGKL/rp7wOmFAuXzFjfJrPaLMy6p166RWYvWQbnTUtUzhVcmn16a7ss0j6hhRJwOrKBkfOaPJJO"
    b"H7/zXp4jYVXaApmGl9jQUh7Tq0+gjUF9HR8XxZlWkX+qx+cnjYBYGky4Wi1iolPMrun2Edg2d2kmieGtdA7S7UfVKuPW8bpvukZ9"
    b"OnLvi/54LPkPRR6H7iRgolGcMcpWXDdjRs/Q9mHotAc9ld47doz+inRnhUD/mOhh2Gdz+hHHgjxb+jUNI0un0QhXh0Fs7LHtX7K1"
    b"dS0L6sBB2ndH9JNTr1foSUMupwejlTEekrsiuFUu4YuNy43Dukx/nRaab7aQnv9Kj2judl9ca3aZYl6t3UZaNHxV0mvtJvpPbfCX"
    b"ETiEc7PGZGagxYr9hGI5VequNreVhiEQkwqXxXOeACBAXrUtZpaguJelpfIG37/l/R/ELZcWPwtlctZW2GM+RTpHetPjqzsMPNXy"
    b"WwuvaUWFxJyVde+BkzSZzzcLvudn3DYj2/0NFYUBgg1lW3CWUXw81fvTVTOye9SSSeR6MGZfSrpx7EZFzhq/eqAffg9pbd2OLhxQ"
    b"UFbVlepe/SW4tjMLlvPae89lu2Zt+uw6QtRee+zua4/H4Wdw28ytVb5xfW52cDEQ4ErjJqiSW/V+SL5D0PiepqRxnzb0NPpt9pHE"
    b"RppGlV+lVomWLRAXmlPltoCMe8UOH20FrXaMbnfKzCJogyp2JfflqGnFycuY45eIJVNLnmeX8vaAY2Ms1e7Xwhec2Mjmr87QewDl"
    b"JPd/H3D/LDcnkdTbXzYD+3OMjjn3XGjQ6fEkzIj2UDI1hE7UTa8DJ7042Kp23vPAeyG62uIzbdR3netpMMmZjL+3wG0PGu72+jGs"
    b"Nk7A/Yr3G+UpKUW/JLIfe69B47AfxSv0PNEjY9Qh6N6t4gmAWnrp2fvzqLaloD+faHY27Bjho24OZy7Yx79h9fMFdovOX4QwDiVv"
    b"P3x0OguBIWpgk2ry81VpA3B5DJx+7hd9pyWdc5lbvOcRZ59PT8OnPAsbVaRxnTUP1JwscYl5FlffCTsed6r5MBtyOSk2euGtyI0D"
    b"I5wbpXkOk9NjOUfj+bXQHI+f0602CsMK0M59858Q7AYrcn8VvHaA2c2CMsrY+mFiW8RgAXvhAEpNh+wCPPmuz8x16K8sqxyXcMlq"
    b"gghRrmQH26ttpF3nFppduGsvLVG2bxWUaU7cYu4K1PO9bPxID4BneWnZx+wpCj9OvXL4CtGkfqAP/KFTvfVQF176k3pn+Pzg+90F"
    b"uLWPaaVG1BtJoD+fXg0pr+tuM/WjFrUR2KXNYMNtaM1sdjV0zZG96o/M5Q9IC8M592rxyuCJhx9F8EsbNDsvHs/kWihNJYvzJiy0"
    b"BwVpP6zKJ3hzdG9WBhN4hnwtE7yKRnc+s07bq72/EDc/vkGvBn6kBg4Cejhwb+uV57f503L662Ijo5HWGwB8T1MVS+AzuoIO6GPP"
    b"HipL56jH2qkGvCZRlR5dWru17ZeWMSy3v9BVhZ/D3lq1nk5vV0UGx8X7Qo4FYZRPk5TS1UOyDrUeVv7twDWM2tW1vHRnwPY6pmCl"
    b"3vsWJ5F3qVVr8Bc3XruLb47e63inxlfoLiB9OvxUB33ePQaDWu869L8lZ1vEX7clVLUqJ27vosj0JrKfEdXB/yve+LHG016UMwVu"
    b"T4u+6tPQspUBVxPmp2oat9qq/Y4ApmIyQ6oxML9SPY25FoIma89YCAdxV3uVFymn2DROYeasDZw4feleK7VJWCdfBjzurMGZt/l3"
    b"2dtpzG+h8Hadh4eD1/R8oL76i+z5YE4R0Z2sdInoiucohnvWGjqkBIuHT9Nf/DFQAs2FhqLZpRvDjemhcdHHWCfVMtuiphPW97OD"
    b"sy865Sb+q92uluhRFOFtc073hyl8fwLzHskNy8IiJUbHsW1ees4Aqj8OTXK94ix39iGjVUops77InzKk7Vy2dhnCv2mCc5eSjh6u"
    b"YbStfi+XOBht+nwj4v8JLPcvAZXC7xRY9vNRlm8d1uQP6D5rNmcq9F1QgHMK6sMHpKzrTbwy6j/IBxK9xCU13j//1hcJOBky5Vpa"
    b"k/NVn/4jnsjnCd8nR2apuvp1H1b98j9XWcLbr+P+NQnxGzdEnuLws4QuEF5dIp1A1sukQIy/et0tiBYxIQng+2warZgv4ODt2WGp"
    b"7GtrQDjWa2ZSQ76e+pTmhZqRhSiu/eZLa9Qz4vrDgUFJnjfOMlkxHv7AVbqdvZN3tUL6aHEzgIHR0SJi0ReSjvMopo5nZDFfKYfM"
    b"PV2kL+wB50m1m0uw9NJuqqe7GHDoizvZux005Qq+G4BJ4NWf4ke9vhPsGHVF2Jihmrbg3wx7S9PaYMYNZaksUU45/hBjGWZP3W1F"
    b"unhT0xqflmXamsdCGBcrV0uC2n2XBA0D3NhfoQK0j/UBGLrB56Dwf9yy9psjPc/58sYB193abrGjNfsGDFP2fWQRv2S0ttU0ZM2A"
    b"cxCvfZBG8v5bIEyNQpPlGIPe1ILwb48e0xzXO8iWTPCzeFulrL1j2emhVQZD/vOFlO7G+kWLXuMvRQkxzd6I4zePeyF7Pa70ysgK"
    b"Iu4LD4TdoO/nzGpYs+RVUZ/SDcO5FpH+t4X+oMS7lGgB9kwVPiZJZWyuMj7l1MyAy+sHUnlV6lEJn/+KdNk6I+6kwYU97eoqn90r"
    b"zvBetI9anDE6MyVpDzCjg/waYe4NLyIpTNdW9wnu8XWVt/SRtb6UphG+oMT+fkYGu5fNdobCbFuMAfqPD3XY7JIxPyCd7TqFt5i8"
    b"Iji7TrJ9Naufu0QwibtPVHRbp2g8m0KgNwQuI23yNLBv2GQbz+lxioLBQ9wGK2/NfMoWtFyQSX5MFYbhlbWFxnbUoChEWt0rePCP"
    b"oEIMpG3U/dSEk70KRetzf1ppBKz5uAeaIgrAXo/gGasvgOKkH1ZJcSqAJmBEBNewyXO88dkeM5GhKwa4e4imV5PNuUf2TGLyPr+W"
    b"w8vwtqj/ixZfQ/8+b9aD6EnBi+H1e/Tpx/eDXNoePnqy3JduRYuRarPeS/qc1+5cNKHuAidNqmHzdB5rM5fhV8lkM2ZZ1lPh2WXX"
    b"ON2qzLpfs+rR4JyfoR+65exHHu1a4AjGXparDgt9RQuP56ZOsmUuy3RbbC1Gvl0Jk1n1fN2s1qDwOMRUd2Q0Z3hvVDz3zPhKleuT"
    b"SRDG4Xcwkvoe2MkJwFHn3e9+eg7Pv0dte527lpHyC7wPX5629ZEcgUrSdJZ1ajvRn9Jz+FLTz+u4lkOraW0yseUpmCm6ewLO2ulG"
    b"uftVXVyvSjILq3eBdbrq1U8tAOLGPjC62MHXwH+Ga+S+SSHEOr/OxS1YLlXTjADsgz19MfRN+9jaZwYhGNqVmry+aGzBp302DcXV"
    b"5qpULVscS/KM+6yj22ut5MFBgiMqIUvDg7q/uddJw70vH9fSb5b+PYhTY3STx9YEwRskqUPHfjPzufg+wZaXZs30K6OrKdQA9roR"
    b"wXocrNxDddYA9EVXxTcnJJb7eA1aRUoC1ZwnzM6T8oKlGOCykM6NwBtjzuSnJm5kHNwYK9ais78upDVuG/VqayF6N/bdgtYDDTqE"
    b"7HhOSLVBhvZY43GnvSrhrg9YD92v8ZV2rl0DWxQb40nTat8ZtEug6wzZ7+1T+hjUTrPacfIrqLrHfmYD0/1V6IDedC7WSQt+FU3w"
    b"5rklnxo7/eyaQ/mwhPr14XK6vvhut+11288xMNeK5Sko14DB8VQch2GjLz/F6HRo7cqbpd74MhJavZIIF/56jYGM8LR1UWCt9NmB"
    b"CngoSe//b6lFg0Wqe/rwQCCUk4CV5JqKqAYHdZVlZhP/aC4uuOu9i/UoDtHq/T1J2js+KTYEPi/DKW2XXc+8D2uPVXn/awAmHZG/"
    b"jMnTtT4gSxSi8YriP1/tqUX0LhOqu3i3xLacNlHu0zmrN+706IzXuRZPaSnvW5zw9FTjpcMlQEfBeRzIn9u8VeOOPmwjM1+qnENs"
    b"79P/BjBasYuM5qPPOOhY2hGiPhsxYZXXyEK8Ia0PVF+68iI3/m6bIDtXv0rcHsbtcM/YZmlZpU76MkQGsHch9exSXUFkG9+50eag"
    b"gXUnMbzRGWv9fI2opefVUTOv9Jux1RPwwUFc1ofzQWnbOoymwv1RoDvrGt1VjwNrnTRpN1sl4JO6SbBotFbcCEaVHafWMVrmaxB1"
    b"MjAABH1LnD8TYjSxlYd8/P7kbUfIMTx7QfXf0UsrH/qvdX321KFh2K8XxGLK3u02s229n9Uq0aef9jq+CtcRvgqZnRCC64N6GmCu"
    b"5FZOSDrag1tFpoeVsNRVZ1ZUoj3/+xx1J78BjNT2Udw3dfwympw6PbFT1qiFDjA6nC4eEXMFTeVhDcbDDf8HbDZ3uwttFjjai7nw"
    b"CYzPNDA63dud2jiO8MfJDg/D2eZQPkuatipIXDuN1XCMQz90e//Duq3oY3nm8SpZGRcvTWbrgNRrvUvb+8GxGifKV6Qf1b0mJUPm"
    b"3hTnC46a7aeJUi/60ucDhLS16Zm7+FJSj4ndurZn9+MouVIsvH9Q422p/TNFzbAGpB2M0YVzZ0LK08Dksd7t55BwEbDFbHvnB501"
    b"7hhlokaI9vPqb+el6/DkR4NlTb0p6kltA+B19TyUQXdw+RD1LtokMOd0uWWMm0Lj1LRGP4lv9dh1qGYPnwjwy2YGm5s/gKhetMMZ"
    b"VSNMKeKWWu+ZD54+Pm6LPT6/0DJ2hjOuHJ0RSrdW5M3dlm1t+VmaaXsALHo4kfFC8flUzm5VbmW00/vVAydXDH71406pMCX8eDnI"
    b"7QS61bdRM0Y5oY8N7OWpK4cNhInCas2vRPo+X4kTJoi2GcxG51wZbje6Xo+rRv2P3Eq10X0j2k6gFNP7Cbe20tO+/RuW+dwK8Bqr"
    b"0MuJNnoyjtGzUOqla/V6PnmrYYYf8JY7UZcXlagjbU5cc3eSzV/QrbzfTOgEaJnXHf+d1YdMb3+lyCSsDUjPY2uGtZ2n1paiiH/y"
    b"tt1Djv9+H6uY44Pljtarmwi6t1uSx8JkQ158YvI9uEYB+jWEe4urZ0Pd77/nc0KL9OgMN6m6M1k+oYmwbkjX/qbRb/a7pCDgTSQs"
    b"Xe5Kzfcj4ccaycpf1uxy+XKjCuBzRj0/u17PWYam5xPpqtsRsPWmfYRL4Ge6r6vMctOgP4hO/iFtAzhdi7OOOHdqYL5GGsP1WJ9h"
    b"K9sr7ijMRdc2dSPtSvfNryfyCLR9WHAJ1Y0aR6s9q/diZHlqA/j8SO4Nn9iQRzdowtH5TW9lwmRpol2J0b/nBbXZhtbFsJ6o7LZh"
    b"VpJmfumnNV/ruDD74AfwhF378kFhK78PyOByvQ9jjZ1XJwbt6WlAfsvXoQctXztj98JOOTjQU24IpMRguoT10pceuitbaMejl6mc"
    b"2Hm2qi2jGaJq5dKq0eJc7vyxaYLCR4NZM5yWdXhs/dRZzLonnSyxdNCs22Pwyfy9OmWZysLm4fKgCZnNIl8JyCaqVV0xW+0rfzB+"
    b"f9rJg/nyZnbRcru/dC7Dd+lsiEn4HSOskkQmGLORiwylrN2lan9B5WeO36roEHnUwg/Kd1xsFiygzlBkrbbzt8Sm0Aazi1AvFy1/"
    b"VBaRwSDDF+S2Aud/G12lK0joL5Hv0R4fdj0UT8qR2HR5Uiq1FoGj7mcZs8S6neGvxtQo4S2u6utzCT4PjsfG5XSZehv4AdUe5wym"
    b"UG6FsNtBM4rgpyhT10n1iiRZt4Y3e9btuEiZE02765gr2YgDhJeD3W3Yj5KQ8fk130mlYf9Zff1YY6MP3aR71bWJV0O4LS4jhK/R"
    b"wnS9qCnv7h+8HZZrVXNkTiO6DNtit5DN0JOHAZ5g0Qqa2d/RACNmUP647w+mm39P7Zw0n+P4f+E2KNF0WxFKP3rwFLftFbXbsME5"
    b"3p/vhjecmuBCf4H2lxxEp1VtEbxmf+jWgrxASw9qs+l/CpTj74aw3i467cUyJsH3VApJlXawv4AprqmlBja7pPeC4x0/yRq/rhyy"
    b"bChrLF6s9hJGT+ZtpL5ApH102riesxvz8zu60kPiupSvsFjxOz2jaok6dwnziU/O3HfzQdCViw2eiTjy1420ZRcz8Nt1RuYJiHSX"
    b"hXfP1c9o0w4Ng5Dj5oBocEnRoDbdilfu1Kp0qGb3ZXO535NgsMZMeGqZ3ZSztZqyf2i0fsHPXIeLy+er0YRC+1WW525uT9+N78Of"
    b"lHetdHFmKub0Wr7Z/+xDzITAIrmfxrcaOV2iterUb5emJPRqBWbelMyrlfKdZ7b3d0m3vDvcGvby9vcSIEkYrz1qfDdlMzjmGfr+"
    b"e9WZSGKtA/Z8NJ1R6H1nc4aqcvDPlmcktHBUxw1n/aQWyP050R9X+LDn831phaymS/mWVKeLJnmZTPiNHK4pYlH6nubNEvwy9NFD"
    b"8yaZAEAGON7Dk33a+5T+8jbqtlKoC9TGBIo/M/CHmKSFFdOQFtXrdAvi0nbP4nv/X95BzoaXSXO3jT/dxnF+8bwH2ugKg1pP39WN"
    b"Rb8f68AmPrbnzNl15idE/z4ORDdtz4TYIlfB6j6bn/vjWzAt3PNvQMguvKx2eJoRTAD2z4Qbiim7D90mVtzZrN8S2Ja4qTKk1XWx"
    b"mrHAZYdk3mp929gLYHm9bWrXJMF38n5sBMzmIgDxPX957Ug2hJw7EWooLh38p/yWVXwkNZDB9laWnOPWS6nJvNYkHA2WgvPbuKav"
    b"aJRRV44XIIcfovi8KS8b0Xqn2Wnf1tb3aQOBZpUdQzw3NQKJsP4Ofo9w7anRFTpGTXQPMT9+1cjnfDZfOGlTuof0rDX842LBC/+Y"
    b"PR9ABihOpzimTdxrAdHOm3zRh/K05C3G8CAAm67V8htHocbtGO5eVtb9jCcv1V7RNknIejOCXamjoOL/CCrjd7nXzbptYXdPqG3/"
    b"Xi5MoroQJ8vyxd9zO39NZfceDWyVW4V9vJ9DoO5DK9eukMdLa9s7a+iXvqd8cS/X6OxQh/qz5JROv1C5O3bqQ4/PzM9vW2DPYjHb"
    b"Kyc8IwOgfxN760a3K45vCuNkI3CzkcITej0I98ORu4GmSWdKfBvP7saVULe7ibeppj262CjV0yysZivT63gtdKsW69sdZQvPxwHz"
    b"9utf2Z1LuIvSEbgctj+6ONjO5WRBEWsrCGZvo9s6fabnU7fQGqRXVrubT293wthxIHr5fXAhq+QQcNKwsZ+6MS5Pbv4h2jTWlt7o"
    b"Qjf4eP9qzTv2+SlUDSOkXmLhVdL+md5AzOJZt6/5yvgE7sDmW8ds6ugbeihQVTdYS+xeKE+7fcuvjuRFxQnP7tEZTwd56fGd9p9N"
    b"NZfMszZf8UawXO1Y4sZIcPj6DUmSe13ajnVw4++/VEASHVZ9tgx8wiK8fPAf9xK3qYTEuIN8iM+zJt9EblTAsony0my7vs5vC2cA"
    b"68EKnEK9xvRA8ergHZZqx20JhV5OAJEL2/4l/NNN/Mu+f+v0hxCqwZwXsKeyJZvOdEyTGZ+dqaA4KifInyETvdspfwF7+tLo+t+S"
    b"67jYXmhQyF6yncTyj1aOYPfr9vas0/UDkyw6ZWVXKNZB+zUA7+/LTe8FsFMxnj7FC6nUL2/xuJphndHWnVa4d0gNHCulUPjxNrjN"
    b"rNRufT+1KJK0KN1AaPqXBuuYhgeNYsgzt4hUNCTfw+vQEIHoKBjUQ/1ZvQZVQVHIo6RyxGEG/9ElZzRvTb3D94FWkrekVCvhqsAG"
    b"vTWT2LSu+ULuIXyGUe0XpoWxEADRATy7yaelBWXrxfeL8dZovp7v/tFmQQYw/Gbyw+yjk3n/7FtRW3rFB0y1OtOr08W0ur7ViYqN"
    b"lZgpWpoDs/thTxF+Ec5hSoMKfp7Gf9TKR7NKfRKNrcC4bE6JgHcMuxXW2u19NQOI55duIKePKPzsQ6fZK36n/XH1y53tRjwO7wvq"
    b"YTHdiP4cs3Pla0h+bXJ4fOTXVvXJUTP4mP0iWWPZatQNmQ8J8dis93jIXfR9cHTVdfUVf3182N7KB0i2l7/08Q+cXV7tDEKU9gw/"
    b"/IVIIbXSirr3wdncGyS4v1B7eRWzxdXL46ef6eiT6cqzWcbhaBw2rkMaXIqpWvIKJk4dxQRro9jgyuMUndhluB1Mhyf6Em5+g027"
    b"4HGI36j8HdUv1+tdzE8SYg69XmpxaP98DI+JcE4k6172/Uo3bRzM+9RpTZ95bYRMAdCjyF0Jy1d40cgXDCvtSpvXyhWlqcXf4nQX"
    b"xLftM/2pSAxrpkGdZ6VzYdqIv9sdfcAtYh2ioAVzOBELvi5eoY3Mrz/T3h/UUsIGQcn3Nb2QFnB3LxN7UF2BJ7b+UWom9FJaPf6j"
    b"UX9E683rIf6oF4uk3fp370H1OKvouP2491OKazth1umPiHEPn4so1PHKsdTmE/st5043uO+mf7D9CmeR8naWoOylZtSTgby5a5LV"
    b"+miySrCteXCvVKXVTpSpOLuak+P4R+Wek8exT6sKe9rAaA8XetbM3NkPeUWv1fAyvu49IZc9eVcfNz5l7lMeHft/r4fzo9SPudyx"
    b"8kaX9XQK33L1MCP7XRlijebZyst9uXpI1HrXXPwkvosXwJVwsq9xyeL1MDsdaXopZsLpQlOwN1QTCi5vCjDlJlRUESezEfuhH48m"
    b"JeLrj4/2Nst2Wb7bPS8/8OTqc+Iis2s8GdTJgsKQ+G1zfZta1j9TVLiCJsZRybcS/zAuKwfYucHJwESUgaXVHTk251uQ+hpL3RnX"
    b"t8lD7h0a02l1/LrAVvIK1/69uRzcy1APbk1vnmgOhktIINiq5Fc6hd5bg+DPxIscW7BS3S3P85HQOlwd6b1g+GO9xOZuDXJPKbnU"
    b"FtgItzvqobec7JI9YBnHdXuRPMxtrwm6I9xsL3F7cloNdtM0mq1KU7+ybnNfG5wAw44bHKAfjOmUDsH572dJFkTloTpfis1PM948"
    b"noMkaT37Bbs7AWta4ji2Mz39P7Gn3Kp05cmcbx+YpiAawsB8XmYZgpGmgxzbW8lRPtcVOXXpUfkpzu1b4P2YSG3IfB7dw7zb6VMK"
    b"/AEWZDjdp0sg6cuG+G1hjBiPrARPY0ehskO7bpyh+/qsR8aEg3vwmqE75mZR763qHGpBzfc6bnK4W9Jbwwci9JEJXToiw1/pkXa7"
    b"7KO8OFOjaw2pM9l5eOCxJTiEabvfZgdEMDZAu8gBLElBtdImMM0pVJ/Z6/bjwmdbsb/YrtFjzu8PS3Wj0cV55gbW5k1+o2f31Ozd"
    b"j71f+8WW1n4i+mVI7Bn1ee16NBw/pL3djuBKY6BQaq6h20OwVaJQcTcLA9HXgGoAek5IaVXs+OpPUIr+Yu6RV85OI0BG3OBKODQS"
    b"jTO/zh59BUV/A0L+Mt0zPUj3hKUVrLMYhq0LfP8o6H1aWRb0cItFakv+Agd6QMdst002U9VbeD3xi/WmvWlVnUL9aSc/Xc5g2ThT"
    b"s0R0B+ooaazmC1nq127UdXz61W7h3bVVzrbMDOaGpq6cScvv3l9+gfqxszsoW05xN+XaOC9v0IEu2o/t4xwPTYuiOeUZSkFU0duL"
    b"UpBIrFkql9okkaO1Z30/JhQHOz0F1ti4+59GGlxykxLsvnU+q0zRwai7eX3Pm0u1CmAtoXsclQdX39pCNXs34lIBqsUoYV1wAGwZ"
    b"ceJV0C453Xl62Rda4u4tPFplCQSGLT2qQozhpepXrXZOP9ot1PwSR4IWqprye9hj4G+7FDygr9KdO9xSMPp85U5OyF2U1Rl1GOTs"
    b"vGHe3DYSwjnXa1B9HmL3zAmsAe/1HyRcLooCQZiLyy3UbbXMSrm0yX/dg6g2i3EpcQTzCvkTg57ur2nivHBbvr89aNW2jgWBDBkW"
    b"UpgZq97QRHgNnNzoVauvMvRS22feq3S4R1MkeqkEd0tj7doskd7FCiZ3qKYn9LL7q3KmjR1snvA0HZTm0G4ud4ZeeXbgIazl8XSW"
    b"mdMSAhW95gf1Iq/HV82UugTF8n4eYze2QamHGeZmtH6giVLlWG9gFaqvz9vwG1X27tD2MRFvrn+Qc/lNS4dKM32UrOz9cp73NvNY"
    b"dfDlYbdl/hLTl8gN67nhz8zqEssyuWr3Ht5Nw4iFvNyMhTGhZVf1ZKNwuKxR/bnMzdGxzCy5R7tmbisv0q5h/9wvRLvFgdUEiN3I"
    b"ch5doT99yaiyMB3p2xeJo/dcRAo40gWurIboorpwD/QrMdYSpEmkiCwXzbTjU8NhIH2/w6C0RfjOUDycaRlkyqMt/HmU2/WfRnqr"
    b"TxdODxszsLaQPHA82t3er1ZpvWrO5wtxyG9u3im7FGiBavgfW+TMa0/UNnsMrtrWtB5KG1q8Fs6B2MqW89EaXeAUQN97KeYAvrEN"
    b"OISdrn46puBheMoWehat9T6rr54G9XwjX5bSl53TuO5yu2M2WVQZqsnUt3j06fgnXMut2+wvsGTAGkC/ryqNQlfkOEK799BAJs73"
    b"WXqd6ntuo7648aZWff/4VWBbncZNJZMIw/NB51RuzNUFJ1Jd8DPngPFXeqevVvM0dumeDxa3FNji3oNlyAnjn+dRa5d7IEd2HsdK"
    b"HKdms6/1Yi3WbgyrFxELmFWuHwO/tdp+IPqIyPVOrb3xXk5WG10XBdZwUEZMFmBwoRo2lEot4bXmm9T00C2dKteQn68rIIG52nER"
    b"7GQ6WmpAzy1rU0S5c8MviSXEevIoSEXkqiki/fpXO6BqwOfrSSXN+hUn1upFadizIOkth47M4uoO3Vn2ZxxO4eIv08ZxFKPGvDR4"
    b"wccir/duNqF4zDH0wMe3cu5U/YnSzuqtTMh3bghgYwfTiX+Y/QWP8Fdn2wnlebU63EjrYPlZC9e/f3stWrsC/lthhV5/2cuGF4Js"
    b"vOom/FxXs2aJPmOPPoYT/Adqodfp/V4ivPw68rd/yMw4zmAxdjRKuu+u3x8OLDutYdOnO5VHn4Hnt3mxjS+XyU1r6Lw4RsE+iZTW"
    b"I1mKw7Y/mETiS4LufK+u1w7l+7uKfomhJw0Da5i2i1nnMzoUxDYcLl+H9wpmDyWVSyBH+0nnB1+cz+tWp94VbzmeQVBjFBVCEzwW"
    b"l9MA9dod6EDw2HpcX5LCQIXea8fx4G2ndv6I8UKuzJ3OoKGNbtShXWU+TnqJgnPZ2awc5CC6dunQjMnPbzyDNmDOXoj1NvvYemCC"
    b"7Ax49blfa+NHvg26tU88o8Fi1O9mWy/bie6u9Tj5V+KI5IcauwcfwPtGF7fqTj/AWYUaUDP206kAg5tXp7q9pXaZnLLvz0KJTOFr"
    b"cR0EOjiBcIqeBe/2eK1HM059zNuTzXf8QfYBXS1TpsPDDHKbFc0GUCJnVDOR7JsxoteLsHAucwBxvboc2CqA0wo/vJa7k/HzFQPG"
    b"G/ihW3fkPDBVKtBrx0eMjefF649Xd9WegnoVSfl6gVjCkcgwjxJObxpbrHOWAGN+A+JFqmDzEoxmj5gdE86JlRhwtbdlMqjez5lQ"
    b"aS5e7Qjxve4vX5368XeOYuEfLKZ5HgiemH42agQtb6caNSuiHYY5of1acd+s0QmCx/cN6oPgWRfasDfIxjHzukwzFpFPB5P8I1vi"
    b"XptijeYcUVOqWp0Sfqhlv3xlJSUMdOqwc79r3495j78jYBI3nsgCbFWlEbLZUCqTPUw78U5P0qzNW0NsJ/vPoR9HbXjTBzc5PO2+"
    b"W1WtA+yFZZkbGA9E1e8goxlqXUPGjv47V7195r8GNgG9npeMPqC1yjTRyOfyO2LFJjT2Z952PC1GI0yor8USBuMnCxRHbeXFN7vK"
    b"TmF7Lba+HPbjs3SXe2i7fj8O+gsg7LVH1w15X+pf+vtrVFxsi7hOy+mnCuPyaj7aCKVeI4npU7zGyd0flp2gKnWpHi4tUldJOQs7"
    b"I8A8G0n70Lp1U0mF+k92AF/FLdyhOpu7pE4H4PssTY4XE2vtCABoNH78yhq/d3Ef8veMNrpDWxhAZG9uNW9nDL7GYbWy/HaO+3Yf"
    b"LA2PmxIiaXKDmHyhOaNNaaNhON32iX3DyRqvcFPadx7zmdv9Wmui8vDR9fxy/l/Q/rN6dcDZwH9ds7Q93yfBuLuHWidSUwv6eWrq"
    b"zPNxmbaey/2nMDuPRcUyFQhfX6dw3h5ZZId+e/h0CNZKTvm+o2vLgV1p9pqP5YV8j/+CyrXE44cWeP6JYWmd3uPALdlcoeUBCsbz"
    b"l+H37J0CMycm/0MmI/Vd1Lxy/aybezo2m0+mBlbzaeKOu4N48aruz9OgJSTuJX3NdhX+onG7qttR6y+PVvQ+Rtxa1s+Hj7zkfZ/H"
    b"XmDz3fqQb7h5y0Do41c5c9vZQJxFWD1/tSxaoJF8max7+DyUmMRaNcEbekmwfczOq7P3dogSh8/WDf6q8cxIKI/spF0vlcDD0z3P"
    b"3X9lYpBYwk5WbaV6caojE51msdcYPrfg+x8Xx80dtCU+7RaFu/FDeAvowfjWNsx6YwDl6Dqm8zNl+fMRdFg/aOjeus2zdDKuwscc"
    b"Dr7y3FrCxfgn7TC5J2uuJwjc60oaKuV7NRYul4Sj1OsyRuHpdiWAm3KzVQ7So6KHq51xqU+SfWfYaQ7sD70yDkvuZlQWo+RVrX29"
    b"R4l6W3coYYu1dRY3qmWAl9+5qicpJzyuzqsnY/QCnY2u1Mu/3fJ5/babIOs/8PfRZnuJScq08ebHLwISdo/CNCE+AQ4C3PsGZQrl"
    b"+vZUFwtvX8GIVjByKGC17Ik2iibNyej7K6jum/1dpUJT5a80C0Ny0ltlM+F8M0dDtSJiKYsMzVPWCHFBiZHBIkOGQJ2OZ0w0NZ+j"
    b"5yrsVIOFIKPtbyMuRAK9MwojKB8y+Wb3GVfZsgL3Ov4q0iWiVwKd6Ud+hpoPdVED6k/G7PJcmjMt9LU6eQrgDwfD5rJ24f64+3DV"
    b"zbdyttnSw7y2fvDfDjZtEZMS4ZLfp4nVVu5haxDPWVMX5scEmsTERP4Jl3tQ91o1p7QYWqA909vB+ATmLZNGJjsVm5XJOrhItgMf"
    b"MMBz/bPBFrJIaoImsJ4WDFMhwM75H9h8dMxJFZtMlgjEYu2ude3vHsSjcRZTbBaWf1kY+pxajb3XdDv75+bVZV/5icYEatrlo1Ju"
    b"5sl8b7Wro/FS7gtw2VexmrVeVxYMYn68SIbs6UNnyYrkzkt+mgS6WcmR5S1E9CHizIPXtBfcVfEHOVsXO/wKxBwSGjBNitu+NI+T"
    b"IaTBtNkgjk7r2O3438e2dOGWDnZ3ajSVhW7FFJev04yrP4jWcDkNnTuQhMvnvDyYDlcRRgJJV61umuv77Li80r9w60zemx1PHS1m"
    b"D1rLwzw8CNH6wF3WZtmdror+azxe0GNi8EI3h4ecN1sFLJ0GV9kuz1dt3duQ82Qze2782Li6l+uHvXSPvoNTh1eMPfubWgh6ReUX"
    b"mA7iqnz7vOP5ZjTeoC/O1aTRR+IDdXzQeEvAsW/EAelWxzsO+wdDgPflmyjNfaIQ7GuUfP6yZSXfkm00maEOVWbuBdMV8nA33TGA"
    b"4BB209/8YqDaHoTbHgoorcpfqInnPvb09+RF6pJPcGf7XQjilyM4G2Oewlin+T29FUPS6ct1lwCXplVP2MZoc0I575xezPKhI01G"
    b"t3rePH5PXH2O591zr/qz5QkJJczueL2dCOFDh4PR/KnIHsZey436NymyKlpj6u9lZ7VO2/B8vcJ79PpjoPROZEat/jGxuncZZfOR"
    b"4U0knmJ7DfrZOFVDezHnFSnVb878+Fsrj/Z6UoXZoY692WSFs1Iuc5A4uffFdKiowT2/rs+LPvsicazCgq8PlMV7622v+iw5nmdW"
    b"f3uBMqLVgAVo0I929vQcbFtvoH22P2aaaW5j0nd+rDH2Itsb1Sp1jm+nO7anops35q+BvfoXg+hA2lXJ3fzhdl3801U6buK1Kqcp"
    b"PzuFnIXUziiYwpueeD1uaWfZstKE3m5eun5qo0UXvNB30aHI8U/aYXTDml+/8iBpTZuL6qZYDafTerciDu71pQpPSrXiSFH+fqM1"
    b"3Qydl62x/REb3zSt78ptdFlyj987SffqAqqz3Zq0WsYaG9Ad1q7mnR5zqFkv48dE1viYKNVd0kSsP7KTjCFwcCbB2JIlpRcfCeG+"
    b"44fIlYEaRfbN+4fJXKXu8rOZaatQqQ6L06f0RxPypfU9SryF6/uH9fnb5eLDpLqruzh5fJvhL7KvafSMbL8N2pAbH/W42CXP/Q7Z"
    b"VSmRuZyvJI018rZrx/e1JI/x6/QqutfSuH8SqvfBpo95aEH4UFC7JqqbvwWrRltb4l1cy02Q2VuVU7v8GoG/R6VzPjn0v5mRS906"
    b"2Q4daLwm15pWb2oYpszFfQkvkwtMMOvqqinjptWdkDFmDI5Vsg5s0r6qna6TWb1TGjSG+VDEe9PW/IjCssy6+fGz888l6neulBeh"
    b"y6fOJxFsnuh+WbcPeucpTGyFx0iaHkeX/vwmHVxoRljLemMatTySJ4yBFc0QihyKiJfkJnk1+4tyr3paALa8zTDIACU/drhgHl4k"
    b"ufQzRSXaZ7xPKSo7U7vH8dToVdWwpmQjhLLP5bA2K1WyWtn8Zs/BtD5PkhArMxZdDS1eWqn9BwxVclL8Crd1YqEMKUzVB9uNHtih"
    b"7ll6XXwyS9n6/kQQwGOLSU8QEoer7RIW7mSirukX6bF/S6oPonho1EEswZQnIYvy0jWgorWnTLe3ToZRk37U9kd+27PH69Vi3bpr"
    b"SK0xwBidKM2fLXALtB5oH+n8WmWIMRI7L85Ztk9t2W5GHFLaU9sDs60sJhW3oahfZwC1ytnzSHhJ3FqaB0l65eMMycJ0eXpsY2V5"
    b"EmolrVd+7Hu5X75z3g5Y3TgtZyrzzn151NOfXCBAZit/8e4sk5FoJ1XlIA96EbIv0TIiZc7g88VayVudRis+NjE/sQeDsSTFaN+5"
    b"4ksCMCF0lZ5NiSbKyP7l1ODDrb8sMyNOHt4ccq6FN6HU/ZnjMyNzT0bO2eMpmZ4G5ep6X+X81vo0r6yPapWtnXpoSyKBFjNJwgbn"
    b"KP486j//Ph1hvaGIddej05hCvUVtBATA+wkNPR1Iq3lJfXViDfYjaWP9KybwfU+3Kg3yRB+NY9Y7PIDmW3gRz2AJQMT2Jc8kYtGD"
    b"P2DNNZS8gyoZuDF94nlqcBOej3ic8IgUlwxiiXqda/yuyMwn1h1LiRoG0RyMzd7q16j4ixwneZPSs+qlTh7Pi7RhzKMRmXtzc8ri"
    b"nNJ+V/bA7PoV8dkDQU+HYNyiNQMie0XTE5dflYvLVzO6j8+KQZUmad8K/2Cn+djA2HoAyt3OXJB/6LaFSO37vNhRbzaADhLxbNwm"
    b"GEzJFx0BvHTSOJQotOEvFXivp5egNTTAttbtntd8t/ThE596aL5F+ApCXb5UadGtHT7ZJzuGwFCVF21fTGTu9fuABSZkJGobczBd"
    b"adg8vKLUc3nDno2r2F8prX6JfyQuSBb79gU43sbkhKlZCAF6jYzFYa99IJRa0VEFt2QNz8fvO33uU23Wux+6tjTXA0tK98g/2Wh/"
    b"43+z2bMSP4+9/Fzs/k7PVbjUU1scnN9qbd5UW9KYSYVksh0N+DBIUkfR4PoLrDCXFlJfjtbMPXg2j91s1OaApC5cyK8LXm7HY/+x"
    b"0HGbIn+Q84mct/gxGp0SY8/fr62zUU0iaRsHo9mY39GjxnBe7p/WxGTb8i/9FZSVAE+AkXMH21nCcnk/rPW696r4BPyHKkx+lG9C"
    b"7MgD521lc0SjrSpVrMdvB+5utdzVcJoTE7du8bX2iRZz6luf7i38IkSmsHhI8tscaijApoN6IufGX/56XA/vWxtaIawqHXcd/ltY"
    b"dwclsCGrkkzr+Ejui67a0lWvUUn+XXipy8gRO0P+X8Abxxddm1Ob24zvLGaMyTwWEaytiHCDVlCd1Bf0wH6u2NvzcdyVd4iPPvry"
    b"wlsx0A0OTgpgrDtH76Q33kEcssq4dXdxZCo8lj96kC838z2f2BcwxatKhBZW67wQp+3FyBiAAzDLySZzU9/kevoUd1tkGzOt7N3r"
    b"LMuG6CzecnAtRpjmOX2sW6EX1VdZKjfYvFraz8aT79eKCVO7/EYV1qpSXbuQW/10Jxf3Qdu+w0Zxn7u40AaHWQVw6aSJ0+UGfVTO"
    b"Vgpvmx21Qd0mJVXoxnB06NXsr1XzTXQ7gQWtWMKrmhNbMyf/Tk616+a1RZHHz7zxHKe8luq61hQ33S9W3CMQtyaeMqABvXjK9dW1"
    b"X9u6325e+LUBfacTEokyfdpwBxeqUlAthnAmlc2uXL8qkwdM3qQL9vqo4zGnKHQdvPaogP4d4SYQZcQ9O6OzBVMyRz3lxU4xrVu2"
    b"ncNnzMR04+riW7jxlPFVtus6Q3cMcGw6r30YXO5gnjPWnSfzZEYacbqCFPB86Gfaiuab0073sdqmP3eUX/eAv/G+vxB9KLyVO/dO"
    b"V7oADrJ62UzDM8t26rkp+fqQELobWNZZ4wRMj4Zj6zjq10t+cCbYZ7B5+Q1e1jTe37LVfZjPlw1YX9LHU6//0X2jQv56+PblXWKp"
    b"XUfvjw3eG7Fg0/FeWNmxpRqkNstNKEUnp+f9NlAu+vB8u4qPwydie3Gw3Vqb3eMl3ndJI4qMzke5+GOlG3JHL0P692+lePfxZ2cO"
    b"wT+rF8rCA1XGrcg7rEc3DsPj+tBxr2Ofm49cor8vh1XUbj9X81ibvYuK9VnPL5WU0wxgJMPXvzewW+SANIZFW3yCR+65UZwaWoIj"
    b"jzdp2Ce7kFb99YWJ3repcee/c6yfLxCNvMtlolsOqdxpV1b7k/rpssROWkHm3p6w5d3oO1PKvrROH2lpwi3XPSMxW8bFcn0lWPc1"
    b"qtpYu3Islv8vL/3H05Usq6oEwW8xBEIhiFAU0FAUFBCRUUHQhSjiAALK4ITDt7/zFt7l2RyQ7q7MrMqq/gALfl7mkh+IlJUD82kM"
    b"+oFz+//Wnzf7KrbDu5d/SfFqjDFE3dtlGR30x4cbuVilcKVa1+9Rx75/2bjf5pto88tfV07eypXFK58+IHMynKob0qgPbv1WgwfP"
    b"69+vYsj7fjQUZtHfmTvdg2nWx7bDqthomdAbGmTcUHoz1rbXPt5z+MDbIfO6txLuhkC59kyU49ja0t/Ttpl2dzoEbPqNxa6WWDkA"
    b"kUqdLAz5eHqrPx64ap4CYR/NymrU5+NNxyy313rFupBtXR0M120i3Gxv53JTnG5HgxH5quhXnaswPJjy/bNq4KCIZh9Y9lwdvwdY"
    b"fTQ8CvP0pcSXOcJZ3AaaN3q/WuOQ5JFg6RrgcdUgZfSYQ72nyO+2/CWgK70s2xmj4PxVHQa6F+vNnBq3+npJVFrv5rj5F7orQ6BU"
    b"TwcA/aydzoavbFmVwbRp/EcX14qgjFQMqv4uJ5UPL84vtUjnhqRAdu6VD1p2FawuyCiGRKuC82I2lT5CSzPbTYjjgYhcDJrbHaZe"
    b"/76K6m2ZX8vMN1iQHwNtW7nAqdRJSOWmPItGBc0DCy75zc46O9aUVw/q7mMNrn/aovnSpRt/Y+E6Wb+TvmsVFXC7/U5mK6aNaLVw"
    b"JM+xU7gpyPhqArfvrcbWscNm8x0q/PyLpXivdxAr8JTfF5ULRQzLg0PxO1dtwL+SU60sPXvAFoomWHFExS6nUwrfuIPBqEBghjpi"
    b"GT+cEbQHTCjJRndBdhgN9+tufhBIf9SWS2ubuGnLPQzgjWox3cyD+XNGphuDq4W7fyYIU31INygFQY6trP7Y22JR86MrAUzHtrOu"
    b"rF7e05ks1JtvaGRJZANbpyb+YBBuMm7FYt9xqcMtuOyU+FXyy6aLkFut5jjJz1MzuOCXyjkvV9f/0lnd4ah4yTdSDBZF15vK1QYV"
    b"hKrUt+sd/7pjCPi7ITGJht5evlo87BnaIJBemX35i1tzqx0G7Ub3iJmKgxYbUUDe6PkuwM/FubG0b98SeLWd868xdL9a5QPU+gbj"
    b"gJhKVtaKRB8H7R3K8q6MwzmS7mjrSU8ek06n1AYbIXKhWXXw7Kub23FtPnD/IL3TV1jstyM4cS5x8DW0C8tpIxArf/aUsd/8UiRj"
    b"WNstiOdNuZtPjaSR8pMUtfyJ3ZLcvsqz5tRB9IL9muDDv6nYrqV2whzYD8PmErC8IUybyqp2i41iTKmPnnkukMNy1A6dxFUsci8e"
    b"TThUfv5AvqyLSe7lr3t3pdH7Hvan1jBe/VACvPONnFxT89Iz0XcPcWQL7lXd+2BVWD43Yv+4Gx5f09MOG1xKuGBWtMoE7EGAd6cV"
    b"eevE1fut0OmajBe/c9WGkGIpn25ecuGAtYp60skGt+pNjxFp1y24h7/utui16QPtpWZ/mVr72U4GtylPlf4ob22vtAdR6OtIX9rb"
    b"ennFK+/LfKiS7u7yUlbnum/9UdCfbfROLcfCtA17G6Txhc+zqJ+KW4NDqy0GDyKKXZGdZjqzokXqvs1l97Cc47K/m+ltZGQMEaVb"
    b"uSWTM8BMBzU32Ek4+V2CzRQ6C2XJ24X1jTMNfqoRMpojHjVtm4+AIZC2lrXkPDo34ZkwdRVnHCw2Xc4f6Q2f2rKk/h6ExOsiZZBX"
    b"3juyXqzKVrWyFQVrPmwfWtne5u4vC5tnOxpmplG97pVXw/HPodpDoVc7PQ0uEnrEvqUxoBSFQoSSGt0npZ4u/P0VUu0z7XzSY+Zm"
    b"dD7dOgcAZFJoIT3prAUDAr3IN1HhlCcVboYZ53sjPoU85+JavStt3i742+yNbzFC/dp7gDwKZvptQAtbIfmgBGRYdYscrSu1TufP"
    b"TtchyDscTcpfX5HXQ6byIOk/QX+Hb7pwd3xH6nUAhFk89h0UNrK0zKw7qoZVCtk6ar8bAsbPvsm1vAWs3P62xRPDL9MS/x68GyXW"
    b"wHckkR856dpI0YHv7fxtsV+Kvc4Z3qFWQPn2rCi3yjBD9p/f+oFSuu+mOHzhqMHB9WfFN47h33sQ2M+lz0w/0/ESKjPRkHVwGfr0"
    b"hrVIfMNtK3vtcvy1/kKpHGjvwwFokh19+gEXHavLdKVLNL3vt0gNbDF8kTmLIZm6tc1HlMc2kzGDzwyuCDJXZj/Jz8eEe7hFTDwi"
    b"+GoHztzw1Bpodq97/tIbxF2cFL4sOj7p9+cez47LjfgMXu4JWv2pT4045JPpYZHWovdrkRsFtDMq02/60W+vYXeDq1M1TH2MgMT3"
    b"r34V1S9HX3hO6R2zCLy/99V5iijDO6ccV4WERMJ4kk9Z+er3BETsyNV7XjGjdFIZHZZjuQVBwSwaN9uX8wRwerC8vKwN7kTIQ2Cl"
    b"i1d9XFcD6edjyiPZVhTUQC38XB+cjKkmwypjPrBx760jslJWm3hnyC54pBOndDnntKfQ4StNkKyY6/xwSqPLfRNteisVhg+jqFb6"
    b"7qjBeHuRl/jHjc0+31z/qnJxHyh5dpUayWdquOJEqCM9j17pOA0/WzGo1Y7g84UKlgwx797tKVzhN7zjan80s4V70KFHDi4PM6hQ"
    b"J6P8rj9LYfvgU598mo6Wz1G/+ij0Sdf4tTmovYMsHweAjv2d8lkjIz6x1qy6O1JUFWYS7BsROIgvB6jtknTOnKpph0ZZajwzvFQs"
    b"yep5Ag9qHMeQXeoCWI+i4hHVodEN++kIqTa3BDRrGz8tvLS+MeJG6WJyTFdRK35u0lK/qKmTgYF2wHmPUY61JdEfLeo3rRBo1XsP"
    b"nuVz4y92+FLX2/e8mQ8Zfh6l3rtBDKakhKWWZqx5gAbqFGKIg13/l2MCajCu9lj72t7rmaWb0p/CaR5aaQlyHtl9alRa4GuatUoA"
    b"Fp2reTffI63rn1JvNTJtMw3ZN5S/WSUpv6raNO21dVwd4/0N2Ki2+6zsimsqOxx/NhwkT7RKDV1shNljt2Uv9jiTFCnXBpQ7YOa1"
    b"dMUezU8kdOQAOk66z8Fs4T6u1sOVW+0+aUGLc0i+YnaDzkNrXy7zyrViLJVlseWPJZdpnqp4T/z1C28ejLApWLQmNjoWa+mQ76qd"
    b"MmlbFgq+0vloDz8JHPPwRj75e8PJfiZ7SwhstlJWLwstuXEfRM2Xup74r/MC6SRH8iA424Se5TW3wE/Nib+d/h7lffaVpDZjSDfS"
    b"6VQaX6p/Kg6S6mN8shgdim2RS8MagDhO7VbOh1FPBDmC59X3iJqThz6dwy8hZpQ+1Muo7Dh2peTghIl5apJLZVP+o7pkCv3sAtkL"
    b"xqPqDUAEo7+rtMw/MkSbN+V6mBG4ZvRKzZ0ihCNRTY3jNR3KU3G4rKz21ua9f5BTgr+1Sr59FBtnxQa8yQ6DI+/+tyao+lRwdhmg"
    b"g/358pNy1S4LuteRMM+uk8r8pDyYW0DN0grLt8RZ/84dw2OpU9xBDU199nS0byzeICKr0EqUvUobV/N+m+IIQrcWwUDOVcHnYfK6"
    b"rQeggxrkYzSEZ/86AJchfam8lA92M2YvMHt8HCeZNw4JPowTblr/A+BOV1RZQLFdJGdls99s327AbIG/qwpTRQ1+XA+ngD9GdjQo"
    b"NSY6MW2tPndiUCGzGlerP5lj83cp1WqIdavpEfWGwXvSGlWP9b635N8GadnSxWjrAaaTy/7ik8hgbWUpuLr9o1M2u2OKi3UeOe6S"
    b"vC6cNN3Ox37DXnIsEldVtRollK7OmMnj/PdPfmu1MdjZ2rriUqkyMM1btXkXyEm9jC7rSfPWw1JtRUKXILHXdjDRrzdl/PCKz0dq"
    b"6Z7SSm+jz65t7/xe6wSfUoIDpCxvTGrVRNjIzyN8PWFttz39TceuySoq1MjZKh8C2+wUvD8tAflQB04W4q7Smy/ZvBp2L6OS5VIr"
    b"LYuS8eVO95YwVoYfLWZdscVntJskwyQIjNPeMynVX4y2t9t9kTyUsTBaH7u/zT4e9j41o0NKpbMMUmt3iBLfR4HeFKQZnvqzvRT2"
    b"t0Zpef1jyokanvirnkwC8+sQWCN51O+v5/35qSCrxaVmMlui9sEbz8PjOVOgYOS6je1flAZ+8qC5GQX8pW9OtNo20a8doLvaiysS"
    b"mS1mxqXWGWKZNBoBccuNrWuIllvoU7Zun3vJ3kT30jyGmGogwZ/dTh607uPyYbwrrwe2z9JLadk5xf37m8p+deHFnKHWh9hqmLBQ"
    b"R5GaMj+PYuo7Asrj6iyScuhV61Xv2h30Ft8COumndutzhmTQ2LGrvTIiHnjfryVIHU/1dKfcy721X0eks0QsELGNbLN6d/djt89v"
    b"VyqErDbZpNIBlQK6d5q8asRsDfN/e2MJJzihcO2Vj14Q0KGwhOA97pC1F1vFVj3UGv/pxNrn3YykaXGwa/pTrNMAX51SMd8/MJOU"
    b"alLwD/D5KTJIXXV10Ep/4RSC7k+vPNxFb3xw//wRz12Ju0U3UE2ajWSmh2wnfK2AaUxKWQO5BqMGNeGPA+wyecexF5qEilc3nQKO"
    b"92WkL27f1ap/y+LfDtQp6rFrtaX1+ZZ9IUTpkArlPeb9yHTP27Xp5TBVoA27h/2J5NuqciHmNb63OXDhpeE1nthuksaFtWUFmJ3p"
    b"6DWa0fD9HN6X3VyaZIA4KanV4a+CyunhcYk6FRM/lpg0daTya0yOx2tgyJ986Alv9FPcMjelWcDOuLikAZ+Xg+rNHN47FFLP6uNG"
    b"b/DeROPiMTzfU/2YtDqDW7Ke19GTxDS26bve/aVI2mI0Bz271ABG1d19fn/YLBOcbW0xahUeRU9VDqD6yMAeGQzEqrX3xQ6EkhMU"
    b"FX1ibqpF5qq11/S9vBhpj+6NsEb4UtvyudHT2keGisejyx9R+BWVos0IOmd3FG6sSpWQ8pPmWw6obLzvZ1WHf0+xkTk+SBKfRnPN"
    b"mx1d2P+Ynps239Pg/4EhOxBsN6r3bdFDy16HKJYIetnCUe1+iz0qUjZ8Nvx1v5xg205miy0X9eYA90TUl+PeVfyk0ctUWTEvmeQ8"
    b"q1ay3q3hmvEnkDnVJ4NctlvF8lbtDjefngjXgO16EX3rzaUdhW1DNDcrRDWhro4M0BxPfllOMM6gjitx6uPwKNqAo7LK9HTiXvAw"
    b"0A9Ite4hH3PslyqLS6MHC6VQnGwG18a+PpuvHzNwBD7rzd1KeYSHNlFJpsdgAXfGPTCuHY/bZp1zs/56/OtUMnuH9bkl70Y0H/Y7"
    b"9xkcOcB6cN285xSAg6AbUsmxEoe1Br/LG6F+/VyGtIh0qHaPNeqrZnS+RpCCgSe9vYlYFtlbr1K2nRRHH7HbAbBvtde7X/3q9OTt"
    b"PjNbo4szO6wijXz56Y/OTETy4BR4gONP11kslTiwLxtQxZetEH3MiLPfRxpbfTpvZ1yX7V3lkLkAteqG61SaFexUZvXAI4axQ0R6"
    b"mnV/k4uy4pExhBgNPxV7oWxz0ll/hzs+8xYLh9VDdy1IDT0o144NAa96Agp3UprRGmImcR3Cx7x3XIloqKpxxSjxCqTc0gIaeI2d"
    b"43WgtVmNGX7/jZW0+UxfS/J1P4gUqy5G5qJysvQZkewhLgYRZC9yON2oIncKGp+IblwDLMErblHKZqnCIeP6Lod2tawRys3RSmHG"
    b"RSR++/T9uIrLcr22uX/3u1+0GGQ8sDpNuEXp5k939Xm/uljKF72ZtN3uuF9OT/1Pb+/6XnhejT1r46LKu95ZBt5C4TO6Mjhh0fIg"
    b"i3/yXDRGXXQosWf8UX61wVoAbf/obGdd2/5S+js7f8Vx/tm+TOeDG80rVB+ElzizrbaIFOF1tQrm8xj3WQkFnyeetXzpTNWD0akJ"
    b"+8mpFBiEYsPD6m24t7sl4LlKkRCnh8rmuzjGh6/GDg+vw7+rttb+AP9D3M2rwYJdSKkGqEySC+FFiTp9GQcKcAurkNhNlD5/fbAY"
    b"tghaH3iBVzby6e9jg2v/QHArsFIaBpWPWkyADFfbJa8EBXYz2dUGYOMHjRQynxJk2L4942jkEJnXriAtA86U/hB8wZa3H2tRupvT"
    b"4R7QN/03c6hYt0X2BZ9Uj9qRZ12oVZuHnQtd7T+tCSojMhfllbF/oUhgsXculAr1l5FOj3SbZQnF4i1geruXbodd1O+PCLM0tbR4"
    b"kmJrODvNqL5V50LhGqjUMmp710Wmdh8G2hW7tJ//rRgIw8PjU82OvfC7MnRuWDRO4MGr1QpH7f6sHS4Qb7Ir0RRHzfaaMhYsM4/n"
    b"oS7NfTaPKhpCrZnGsX/+RhQNrt/DiX6Z4Hw8Zcv9St3cvA6+tz1/2v1PgSsUfVGpk6tbkxXeBWqSw+GpCC0C5l8Nn6vU0qEET/J7"
    b"8lhnWHdw9e3oZDfhSuOSatP1vQUJG3Wooa/LWpHad+e6YeFYKfQuWSJdzv+Tdl2u6xUFuSm3iaDOM4gpaQtFbtVydFpxNz/jcnmH"
    b"a0n1lN4OcPZuNK73umeqzdkcJPjpsrSH06cBszKftJibWHDPlCv0Hdcmccoia62su7PO4p/kEJLtMh8g6s14QRUhGj6bvWrD6MGX"
    b"1ootfm3k7nV86jTnRVgfdKOD055fc5xur1PdO7P7x6vLXqzXeSwptzt/vyx3kzuD5lUWxHBpcaoGu57ZCnqAEGm9772zrjbAx/5w"
    b"n22HjtzbIFbO7yua+hvqNxcHpa/RRMU9EX7VeCsliE0XFfL5dO5zv65AYIyOplNR3UvD3XzcdJh9HbFX/fmmJsTeI6m6SNNErm1z"
    b"1pjMz5UW86erK1si2q37DnCvH8aQ8rONPrV6Enfv38WiqVjDBr7w651pfDHUTXj7IMe5jvrC7fTcOXfo2gX2pbHzvNU9+bmJLKcT"
    b"h182LpWi4HXg40urXDiXcly6eqt2eG0c3zD/9+M+q9/1uDxtH0wbB02hjKQysL/ui9e68jgNOfo5G4RkY5jmV9O+Z5aED+uvusXZ"
    b"9dqf0FMZIhFqY64hTta7y0WAEEmYdDbc8UFm0almkzl9C11q3ZlXfkS6In6W3/hgaKv0LaUzvpybVH6YLpx40Dyfu+9Hmz4/MorC"
    b"WW2iFO+Zgwmw1MYidAIl8Yia8rHIHT46j9Q3dJ+8bF83jmo/7o949+rX9lunllk/P3sneq4INI0t9Kzii4q+QE+e0IhY/8JOvm83"
    b"O+OuKMV+dlKkRaBhVvsNVHVYTAcomzqPr1EY8nSybdI7Ej4Fh+J41dPuXLfNEX2cll5yXAn2v0d1427brPVRQkmj6jnR2XuFroB7"
    b"b7/746dtBFi0ncsFgvUpLbya83Il7MY6aT8UjKpcHR8h/RFnjsop0KTIUlgmYhzcYEWSC+a6ZJIWsO2uon/XN33NVVculT110RDA"
    b"tGm2jlHlkBpVoTp44U1jcAvCmPOb09lFFhJVOpyioTu3iH4Ta2rfWbs9aSKzoCyen+AcA/VIqLyjyavTvT9W4cCTzx9C/xks2/f/"
    b"86fNeM9O4svgnpG8qbywle/eu2kmDlq1JzWomTMfZPrUuP3lu5P1O3INtya8lY3Eo0gj3ppPHlj4ytC5AuU5LJvXisl98GbxkiVN"
    b"m35/KDyM8FellXrHpUIcx25FTl/b0hVEq82YuqeLzWYcNkKCKtfOKzwEc9LLqrNvm1OUs7z2bYT274APzbzm5I+71tAiaddG+3fp"
    b"eV9KvUEx+XbhrPJ71D6EMW0UuQMYGEJIvD1bfHNphqnoHoLeNlR3zwiYVStwvPugQTdrxo1FXSHjaZZV+RnuTnB11XoA+c64y7EK"
    b"kL5IGxJboB8itvFT5SKU5sMf4Ofj3LPGsPOpKPMV8KFHc2bsfGITERjhRUcuiQJUSZvJrQjoSKt5/xKV9iW7ws4rUt3sp/2rgY8s"
    b"/UKmxeRsHeVHpeR/7jnbobar/tHAXvOl86OcoXqpBDFH2pB6Ozn347xvgsDNWTSGkcwklrZaQfdJIzhM7/MldsXQjYm4yZYgtzHa"
    b"n40EHUQrz1K0w17LoA7CLfXuAV6r8gip1w4/PuTptu7/aiIDc6Oaf0zEI8usVeNLk0W9JNVbea393N0/MgA/suZ9mvnH+5JJsgtd"
    b"xzvTvixK093SKb9bPDurruDqeSTO7q26dJmAWueAtcpE+qr4Q4Oshofj5ZdM2PIU9oyMBL9+qp0Ugq/PHCY7q/wpl8QDvbr+hc0k"
    b"y84ued53/uJv8IF1klon4vCiRha/nEO7MDUXynfCApXPwHxaQeJB42+8rNNstWdGCvH7gOkUPJQwy79CkxZcRmmDzyXk9LkB+091"
    b"Uop8BC3XzzNyPZ9omX49/vH0OpYOSyEKZDPrZCXlCc3TiiRBG+Yul5/rHJcGJs3r63ycQXjBnJf+ryVFfG69Va3h8tUNzpQ2629/"
    b"wdFSUSXvWYCI6ujKlHtvESGkhkAoNbVJX2Rz9OXDdx4L/RXSBeeQXquVagNg1u55O6+9RX0OvdvjYgyXv+ryWR/+0lnBIBCCYc/d"
    b"OTJT7bL1jDaEknS6GcR5sRyNvWW5VIpx716897lyWykYLKdfODqJFciuqwINbt1Sj2mu4N6MUN7yAWxWdva23ID3Xainxy+Min6/"
    b"6uGP0P3mKy8vOE6szGeARD25Pj7nGXJolM06f1w9Spa2rH246unmoBNFlqnmciDpdXCCN8SheOBhe9Km2051H0mxV5xy8rICTkZK"
    b"ZxLStAP29yjjMD98Z2d05wQb8bBcfZzMgxb6qmj4A+YvHOV/aqOJzmVsbWpOtOrHI2Gif+b8x+GeV8DJ7v5db26gRXyW6tvFKk67"
    b"pVbACKF+f5j+8zPWJeFXE1ny6W5HL7afkflNMnv7BIBbuzG490Z0qUYUxvWm46PcXgINPCZqy6S0FCkw+iKgQl9lHexM56W0kvB/"
    b"Wyknb/HGkxn0Wtb+yBe9ovBZ8joS8G/S3oQg2mLttLzc9P2IjjSOWsxQkI5CCXIcG35C4Qnjs3vffTHtO3qa7RFMlm+1p2qiArIF"
    b"b6xeUb9Akwig9CIrD6BC1ttt1WO2k6aTdE+1Gnb7RXY43b6v/a54HW4xjRB2jc5turk0zuRur0wWJA5odO09P5vtXWGdG9u6W22/"
    b"KvcdrZUMz09fHFNbPosH9ULGHjGeb2eT4pAA0lMrnSujXmPiuXXxJ+XUGrl7oJu86idlp3meSwCB4LxyM/T+y2Ct1+fJ72fsh13X"
    b"hffZCYh+ha/FxJYjTql9bFynSfY93GH4hFjGkjKFMR0hO0+o1mz+9casSc+sWL88u7D4w6++3zlTRZ0B5D844sVuuGqeEDLZzkUv"
    b"vIM47hn1F5MrxzVb4ZAG4H6F0UY1BtZIFsHg8mjLYsmrjAmjMpFendR6P0S+fF4Za+6JANntV1jnt+Exyz2gk4ZUyfiOLiVWUHV7"
    b"NFv6u8kqecZCq2HjX2IRVbnN7FS3lgK4xVbUmXcl0UdzcVFuiZC7W02QITSukP0qUI0A6b3fUyv/0aclhP8Bvm6l28szJUmgcp5m"
    b"zvAFiunfsUSqk1GqinrS7jHj9+7THYy3IgEiJxNRSsm52JoEZbhL7voJviPcCsa6Io8Wo8OMDEF9/LBJzHhgyEC4hva/K+zMEUad"
    b"mF7d0felz/jqoIcZbQzG035mSLlxpnqtHLQW1TdCI39BqSH0WKZ6F3qtqxVGu/ctKj9reK1fLsD6bS4QD3sawq83g2xWl5uARbP4"
    b"SVG/+lXn1aKLzin+nKnX+kPetf2TsVQNuDaK7z7B/0DUc0SWoxrz9rM4EtnHGL2K3DMn8BLYDYbwo01e95stVsromaLPhHk8wki2"
    b"Xd9ApS25dGTzzvycdFqQ4exIUps9dGSMB4DElrdtWOwbTrwjzSsksC0tWWdPdYXfmlFfce4H+QnlnQV56pFd9TGlWXtf58hovZ+p"
    b"/XJk6W3CAs8sYTE1vMc/8f3oJ1BXG2ir6gdzUnWCjP7WXLEZ7ma9oewkqLeH4ls0flaTw7MaHDYtgfCSRom9stdV539HGiBpx1vt"
    b"Aea7+/1P+97aJfv4+HYV1ID3jphXBzHWCMWflLt8tlOSbO4WuxPLvNVgz9QHr8lgYRPXrxmHeyI7UM8rvFGu/OK464KDLpKLjWPe"
    b"H9iEe1hRc/rVhMrg+KCG1dFE7ppaIyAdVcn1eixC4fqrNX81/EezGUZq/fMnN04UQeR5c9sUn/2J7u3WXyu8++kYhZIVVi+D2eY0"
    b"1y9BpVWn+tGrs/7j42jQMlp1YbOcN5HyWSh5XolAvZDNCYOBuKWKrebb2092n3wcGAxXe6o9rN+82hlw5kLEiNm7etZwA054Z9N5"
    b"s2RpioXbeF2fJVBjP2Og+cPseaNu6c1gj1YJO8z67HND9Q7fweovSl+hKS+w+Sw7TT0q/SVUid3jXt1Kt0ppAx0j12UJMtM70LTW"
    b"P9qVEAOX5s0HMmm5UbB7W83eXdzvllhbkDxmRjJI2wJeGlWbN9YYI0TF9Pgn3QQ0+KAt3IzQzYjNEPAnek6PPBve8MFnsPlD0rOz"
    b"E12YMff7M0+2V6t1wj7joy8at25b9NTDZ6Bh99U7kqCjNnJePfPIbpI6p3NzTNVa36v+x+uOlftxuCycY0lA7lmvo/2mdpRob0cl"
    b"6N0BcmzZ7YGD61mirtj6tMTfA/T4ckTFveJzeo8H7K6mgxtGr58/NpbsCCMvyuGgaix42LUxrwPcAI0DT2BnjvBSpaVPVR/v2or7"
    b"80gvZ8NPMDJAySH1hra4XgDka7Qho9tuj9Rma5zTi6UC14XLtjezJtdUMctP6MrZaVFsnt/GIXANfykvt3XK7J6zmkGXt8sTJA2t"
    b"+0FfNTzebVR/jp9VVC8vF6Ol+GByfV7SdtpWiqLLkEQqM8UdoViIx1vg0UOVuKyusc43kr4BFi6SyiTc5sxgBtpwud9nmMmf/Bf2"
    b"0h8AHYvVDTu/79Z6wV6YAv/twDuQ15f0fIhNz/Zj+h7PHzNpEMgMtXaxi20PoC33jN3TZrneIPm0ufJvejhkq9i8MX/iOOWdysuM"
    b"6Rkf6qWPVoEIlmdTedLdT2tTLFpWd/bk2/pti+EKu12OVdAuyOvjVRvK/VpvuSTQCWc4jhy8j1ToSztItQ6E0RmX86IBGNm0O2iH"
    b"vtFdwC8fcq6Tu6V4AD7naRKkDrca09/3y0P5W/DzzRczf9Nwuvm3vNiqC3J3qiHuvuxOG8ulHtyGVbkKj0s98g92no9iuUU+nwch"
    b"rbARn0BCD3zE0XT5TSZVjQteEgwTxWCbuaNNbF18Zsig6wm5MdfJ4q1ff8kE6GKUmrjowcbQYb7ZQHqu1tAhHh8cRGezvgB9VX5n"
    b"fufzpv08e25/FyZwIZyzJGssGXSUkaTwWjUO+0pn8IDM77AJFo5Sy/oiKrT4JTUa06Of4ydrKkTvcWw/sH48zBRlIVc0YQTm8CY4"
    b"bg7B6dVF6jBWNlelQP+aO7rT4w/MqYe6VnWjc+vmpr1X28C8Nl6tnCratIF3azzgFifa396WqS/WNOc3R3rQhbeduMaGI+oME/oZ"
    b"LfPnw1ebKavK/42atQ/ZqiNVn+0cZZPJmc6Bqyt/qL9ozdt+c6iAL6BNefu/j5pIWBDcMLcnCO2mzI8D+3pajVVruP+pRup+p/XI"
    b"/YPUYEVhIabRVFLbModgvWhm1CvL29XF6LigSd85A72FP18CFHjI+vSUi6vtHPls1LJdcFq321PFPOJGJRx5MbfxoU9hXGuIzDjy"
    b"J3rQcu9waC+XqXQcrgVH7Jkt9Wz26sNZON7PhEapQo79/UXqUV4fcj+lg1vuT581lvzTKWu2FVf55q2dglMdn3JVMDgM1dgt1Rtw"
    b"+RF9pzVxGM17v8zZwtyUFZF5wm580uXJo7SZEwW9msTGspbQpx6Dc6tqRMbXHlOegtXaZbVqHc4UgfeFe9rf5nPaZMa+TSug5gnu"
    b"qWwE6wYjteluKCukNu9a+fTHA8USFR2citB5dK51GEFdRRkWuLmHV2zT/9Kp4lVe9I5eL2oFR3D+7C+UQ7f3xnbK7HSWDvHHrN//"
    b"w5aVthyGA4FsKJwBYk5Hm1YbFEH1k/Fz+1MioCRLE7h+SDSP+VR79IfQjeWxLoCTd/ky75rL3sM/mQF9ez9zKJxVt6fntolewDX5"
    b"ul9hIgmUWXiYz6lqTV9q95i2ULqsUZcKRe8Mbo4Qz9njlw/sLHH8lrfOeZmWrE8y8eqFFPwpKdR/nigUFk5yKaZHx+buj9WQ1O0w"
    b"nwSLctc5dHcvt/0XhiXonMtIR7lB8lQ+GpklsE9ShBBhZzOnIRRx/Kv5m4o4MTtGQyPEcmDX0WS1VYEWa2xehAdOhUgLDuAzPsGG"
    b"Ga+Gi61zCLMy6/m7bIlgGN9SMe/Ul3oI2VP5btNOEtGiwxUMDTJ69S2/ydJyYQXBb6gfV58RXv5MQG70mtec8cJoRyXvvpnuMBXp"
    b"IRXUuXffrzt+mSPKoNuuE6tgab7MZC5m62pS5avJ53IuNY+rfrWKRXaGvhgjnQGb5xPo4U4Pz9/44x/gf8Fg4bQv7cZIGrU2R/2z"
    b"D4J6abFuWji40Xzt7Bb1On5/ace25S5V3GLDwZv5OMLcG582M3Gn3GQ5xz/fpXjmKiIIP8tCV3j55ttfA8Puc/FvrWqLJuNSp9Zm"
    b"MtEqSpaXh+RsvxJH10k3SruMe3UvJKvMCbVGfQZiM2HXK64rJhdK9GIYunBFPrpg63sS7rwAd0J0O1DDhiJ2oCbxZTqTbnPyuzW5"
    b"lztlm6uPqoTMkB1TeG/mPifMPI9lcxaBlsK6Jxv8Z/1/FitGmUljXMyk930yvptMVGWU5iHZXwYMRtnkNB8fGmQR6+ZNnAkEPA0a"
    b"aLlfT37jGUj5zsu5qx+/x4YEU9uxqYRmvN8Ei1UW3BgkJEpWzRvC51OuVC6gmsiLr4/D/OiWC49zd/LCht6SkSlzPoP0R83zR0KH"
    b"BOYbab7cJXk4KW7Qj8bwSGmyHQ7Oq7aTnFq5DdzNR08dycRZMyMpHNc6u+quqRTUy12HReCizig2ei6EDhcxWFm12j2ukzZd5Uw8"
    b"kC01As6oaKK7BUu451dkfjW8Mf+lSJZek2Mn1n34oK7ztXdTR4sHRl6wkbDUHxWh1Bx3r1uSmmopft2H2/Gi1OIUDGx5k/gj5nnf"
    b"v+3H30NVPnc4Ie2jLQbFFDx8av3S2pitPP4B/HORlMSOKR+JOiHajMjwlrDbl/bm9K3Cdy+54tfdWdPcc/NNPe8sOQJOdK2EXT/N"
    b"SbdUBjo3GVCHIcyjet4dle1t1o0GVv3il4B0D3W08xjIppXHj91q6qChwMTdaZdBOTSek1dlFFqVJv+nCBonbWoy1ux6AjLlDKZH"
    b"lqJeNXd/qwCC7Y3S83pph8J1ICyON6j3BUKlBywf4VjGltTQnrcsREfJ6f43DeePaT5rXr9UlaKxgQzLV2nTRg/A8JMh6Uk2J+3S"
    b"zJ7py5ak45A71ampJRdnNLHp6uHBm6fM91s3oDdcEzZJKvS8u6eFuOeVOX8Pfr61S6x/mF+3Zre1SWVl6jT9lsQBpZYyz7Tp88T/"
    b"72WwIpkuZk/71eEgJR8Nzwl5H/f32NHFeti7MsHPrRo885bnZTe4j5C5vux+RtXcC9snfMX1oTPMLXfo8Jd6rAi9e/ni2G5tpzVl"
    b"6zHuQKnQGgx7TALWa5OJwMuD66sMP2brM0SNH1d4S7QnWLSJuXCMI09pYx+YGp1LyqyKeUcmaQZ6t7z6KLZzxeJ68gGFH7u9PmDx"
    b"KU/vnoVPS+6t3h99RnaIfS/FpBr87cn86JnmfXvd96cPRo4+Dr9UDsBDb4q9Tz01vaZXP54WXRXHz+1s3Doy2DIs5ee7f0HQZ4e0"
    b"kvj2k90G1Of9xOXyU90Mklp3ten2+dviQ1WuF/VDV5s+lCSq5cGPfZxcBPQ+oQNrFG9zf8c2rCatMy3vuDg2Vh/aqXg6URnnzhwP"
    b"xd66d7MmVUIjDr9z1Tt7h+nq3v+Leh/L7ykYUy3gkwmnalX1DEy67mc5K6EvKrwf6HhBt56NBRzUzn6L1ub47lCzejt1LBd0uKfO"
    b"+cxbuO6W3e4K7OIkxdyNDlff+aFw0y1z6zB6uZVMdMbVK9W6WutZutE3p67pjPSHi5hedOjNSmK3BOhddl+3EOE2DtV0LTQmSyO9"
    b"NjM8vjo38pAIL1Qs4OGLS5TvYU6NKU6vT3/htpUmagL8sdt09hV6wLlynPFb6zpoPhduGbxkq15GLMPywHhRaf11got1vr67X6QW"
    b"0ubNpcYjuiJ+q2OhMIAhYyo468vvy+0lQPwOsGWubSy0n5OOq+nx4vg8ABOq05zBJTCQKoqgt8fNVdBv6/443FSskalKWNZ9OmyP"
    b"I9a23cZvEl/PC2BAbgXDc7zrBG10/EPdi9J+CNYa60jwtxW3zQxbwfjnu/WumRU2CQAf76wNGMNMz93ioc4a62/jUiyZg85Raj3b"
    b"kVcNtvu+njba65X70bcH2/Rt8WawDl6yxembj97DTpUlZouUYe+XSr8kVgsKX3qrX2AqikzCp10f1yCKJMqz/h66w6hZw6ztGXz0"
    b"XMsF9AOhMWskLvXBHAkmWsrGjiYVreVzCqfNY9jei2rTviS26t/rHZ/TlL7yuS8e/fmO3Edm/G8q4vXBdChoAyBEbn6k6rvw1s3F"
    b"qyFXOeyiY7c+LgVrVz5PB8pn8Ga7obCbFYwXtJujNjQf9UBAZ6Ez6lQ4czcMHzZ9ryDVaHMfQplTdHFgNJ++fqUyaaTw/BFh+Z55"
    b"sFA+7h5Lr0YdnpxOfP8ywxg3kbyKzZTmre21qFQP6qvkrslh6dO7piG1/mOquPFsH/0BvKKfeL4WZ/1oltAGu/mqneR5XA1/E1ZO"
    b"20eA+qJQpOeXO1CQIKrFBhOWr5WXMlA3aYWQW2f1WD9MxIc4Kh5M64g+x7fWbIV94+3R7mAHB5r0ttDgmhljUt0fpweE6dh92Ndb"
    b"5rp3lcFf7hYJ1Oaxlx+VslLDDkA1Lm2pAH5XvmsxWvWhYWc3Acjp/Lk5DSYI4z7quFYB4LZaMa7IcdDSyM1pTU7+MKzontZe+ZXW"
    b"bv2OsUiJR8d26KrbktIfD6xiG36gXdg81WfrLh12uCDM3OTMDP1kSg3p1v0YpUmSlSaThwMrwWvOkvrN6DfIyhKtseathGu9qF3n"
    b"ZZfuAlsXGnmoTBSN6SL9jDAzOqzHP84+iuKRAS5n/mTqUWFU3KovrZdRjct5Hl4d5mGCe/IUVwAR1c5DYn6n2h1dn0Y0BK9l1zxV"
    b"1sDXVRpnq7Bu0slI07NYebcn34WUrMn6+kuLCfMTqHUlmVYF+Zp6eYW9ZOuHjqCqW3/sB0xZs6xp2ZtZlTRbcy58Gd9q9O5yXKnh"
    b"lGJsrxkMDikPPuobDdQG+FE9zJiRfr+VxkO9cjtNZiSvCwUxgX5+ixNRvZ8e/cYSZb7jaRTH+Gjuz1A/tL/fS/rY20mp2/KD0RMK"
    b"+BfyVfxkVmOuocfhM/J9f1ma6J1Aq2PAJBWiLx979b3xre3YvAteHa38/RY/Jx2WxD1KPnk4JgMbgNcaVQxOVthpAUv96e2xW0Ap"
    b"BNl3ckV+9sD8RvUn5/H5j3FV5xfBGrYbQc+8Pp+mPi+8lp6Qg/LV3j0klYbrr337TELEw/rxwNkSwlbc8FIdBfoYRvnpDCRlpLdv"
    b"Rd0rfsF3nQvO9lASOFyk1oTemdPAwd+8hUUnHIlU00+xSv3IW66FAKVtFV/DjiMpq8utE5567070QqfqT/QcKh6CLdW+TCjPBBUv"
    b"qKfrWHPoTji3/7l62r5/mVa60QVKRvn9EC63uwGqqzai7h1/9uJsqWxoPa3+iJskT3yUoEhLsVf0248rd/CbL4CP2B+R/pM6IN72"
    b"i2H99BcvCOgjaF4wHnCvTCDi9xRFhVHBQBPzaH6Z1dG+HPr1fE22wARKzi+2MVllp/52hCSyIrWOyazXx1Gt0uOnRj76FqfPqKFK"
    b"v8tzXgt3a7jvQ7qtzeq79f0TfXOtCf9FptuNrWbgKOQvJ2cSgrJVUBkzqixV0ZE1SZUOCokwD0rEpgmC7QHKfRVI93SaV/EGvWQg"
    b"JfZGFpZMIu/XQjkDhlFnvvgqgrto8nrRbYEYKzcP7WVxH9HUTKximVOe9283CKU0YRZVWsIVnmR6suW5O57MZLQVyjWwciNuU3ez"
    b"7cHReybPyVXLFnsLBXNN8DdWcrmydJMxsxFHGPuxBXHn71nSwFlrCUfrPOtX3xpP9AN2dT4+hzvU9i5ZNLMGXTexCCFAxsChUWNd"
    b"qCvgWnUpvrcg3IAUqX4jQfn2uBiz77H8C0zhZD7esOOXz8gd5CP1maAOHAe316TyWN7NP+a0oHt4S9s85Tf6aUKtfSYancw3BrfO"
    b"VCid83uBv+YZOGQIbNfZUHvuW/fyRuTMy4AIwFD0v3f/10b+GVKtujvcHYXW8drQ2QCYUb1qoA9fu7S/p2YPk/rIUuVBPbUCbjrf"
    b"VVBX/S2t2cfRVUz7plXF9jvk20eK2mSFzovF0uXAVd/bDFHv5QD9lvJjTLdkdIoFom7a3CLYTdG3D+5XYwkzInBA7Wr7/wdY1l4p"
    b"wD+Yi9KbKPDVHyxjiQPt8dSPq/SO3Uypv/XTxo36s/NcWR1SBHio2lPVtHBq90f38PuALdssxEMk0MSDpiCj08uzebnXMKaHkghz"
    b"HRUB66JyuSGCJx/XRLQAz+eO2eQneu05FUfLzYJovIRSo7lIKyjdjv1ZdfynIk1j6igj0uofq+PGLwaKuOuZsOtUDipoifWJlizi"
    b"qGh3DoHDHILgENH92RE4n1+3+te2ELw5Yxf9OdEIsDUmN6FNaYhkra34B1VyysESucUrC9ueF+6u7q5ORC94Kr/JsEJyyrkJ2ptv"
    b"a858+d4D8pSsTq679bJVvaSHa9pdgI/tmOGO1bZqt4XunutMBjt4XU42y/XriFSumHaVhovsS33wM1pmkGpedr4TO77uKvixwYW/"
    b"a9FOwI2rcxh5FDuCUUTLpElQ2m6ADds20RhPr2r2qhPvZdfBhkzVY43nbnUCkwTstbtLZ9XlU1TfIqXQupHNwwLW703zfV9Wlwuj"
    b"BkgD8bktj6wfNK6F7dbdcIo4VnaLEYg4f4iK1hG2MwhU82Rvk1eNmfutZE1cifLiXFtQ2Q5Artel9ep0J0jI+mu727w3w5JeANbe"
    b"Wk6LMVE/c3HwOB0t7IR9yj/GhCjrqN+cpX8bC2XcV/1+P606g+dplQ6Dh90CNVFxukfr43d8+NFksk750AFB8dhmaWeBPtIGy/BV"
    b"0p4Q8/lUehSUWRZOU31A2HUUiCLnPcjin0das0mXeyG7wWl9KXcwuMGhslC7jX1D0L/xPKhuzNAlXPzhYIdmZ8lPwZpcXMqEL44y"
    b"S32Z1x4BB6qEWMg30tbGcdY/EeXeu6ULpch/NK+wQPwAf9Dclx1xQyRe+On5qKYNAP8CQNtb8qrMvlq94MQlIl8AjT1dcLUHI72S"
    b"+gDQZ/fIDy8ueE/XGNjC1o/+hJFmf4GZMI8fY1TKifHmvHSd2eNDlv9d9nY9q+Zx4MCqn1i1nS4fvn/rZ5qWMcV3p4s9ra+38adi"
    b"4Rwi5ZcL1bTEcLMfPwIZsP2i/bwXpT21XTztFVHVyWb36jG2wEx9vkPTUenU8Wu/EvQhKPtSlY0DG1QKF+knNfG9vq8Xn4XUXuUu"
    b"TlX3ArcBSbGS+OO56lPy7XWujG+HV6IuQau+ocznurkUbb83OSnLi9QQ3HBY9GvY0u3gl36jKf2cdBd7rAjqncFFgxMpvtMmNTPH"
    b"dnanNGv1Wu4l3HWqgKp3Vj3keSbq8bDfLzX+KA05BfrdbFiWRhHU30wTZVa5TLTGI30Bs9cNrW1eCqmWw0G8An/TcLKeV+KhrT8p"
    b"xU8Epww/7nx38z1Kam90BoUY0lhFRpE+itMqEDZOhaZG9GAfi5655B1w98elJ+X+H63fWPPHhigPR60W1Z35SYJs0D2Yjybw+9f9"
    b"gnaZxQNLkJF7i+QZ275d+nDO+d57TdPg+cFl9+ds7kn6avz2voGttQziBHLgIVQRL6kP7cc8u2Yvm5dZ8bkenjaHjX2LxA99LNun"
    b"Czcesx3616253fLL+kvptcNnBbhkB7V7bI2PfSG6Fca3xsFld6RvVPvKQKfybnhaQaXTaB932lTGfphtc3jmjx/F7JPULE7w71pT"
    b"7hdlvs/ns+e0zdSd2wJwf+2uiM8WdyyP1421P5T5iVum+0PI2xn+Z0Ycrx7iSaFWB1F3DisbvFNuDYzPSYXW1Jop+Js0CJrEXBgN"
    b"IHrE9IxlFx1uX8+mc1xoXHVilbP2d37+gUjTYL7E9ELH/nyovUYmDlY/pQpWCTUnH+T0x71K98ku38yf9WXxaKcbA3cPaDq7uFyz"
    b"WIfuetqPDdi93cRZWwS0bkGz62eF8uA1/Oi+38Z3mP9AZM1E2mWrXTSeec87y202qROKyR3AYYAVeprpcyHf6WgXf6LwrRfN2Oru"
    b"oPSlnr3xzUU3TsW7uP0jRp2Tq18el2Cq2Y/xAIavqNkfUuS9X6H9Xw0/f41V7o1/fFk5kg+/5DbaEWkALQ1W9muM2G8bLe3Vhj/A"
    b"cADT9c8td/Pr/qWl4wkKrTuEfKYr3ZyrzuE9HY67VTD3Qeeplrrnz/DcmVwbo+30V+lhOnNte/Mqg6pDZPDDnb498D+irmxXWW4J"
    b"PosBjUpIwAEhgjgBKoMgKMMFKgiiIiIqg9Ozn/1f+J0H2HEDvbqrurtqIXI/pGRgcKyTSO1dX3PoYxxxk7qi8rJqEAxnanHR4eed"
    b"qoitjlWYVGG2k1OXME2uWBP3OhHNrlJu8H70FHag/Bo/Rq3iMXtYf5IVef0h569Dux+cqXR8vm0W3QnjltGpLh1qlT+E/LT8QU9Y"
    b"Y+oJEZcmZyH5lyiHs1Grmo50AkZmEwI++wu+KVZ3d/zwbl4py1HpX7ZI1iC/G9N0kxB0ur7TlN5ei0BLnSFNd0zJl3AFTrbkpmTu"
    b"r5BHJDVtpwXRYVS30mdpK2FoSinttILMk+28Y2uwxsmfLTpQ7xGomhXf9dXR6xcWsUKWov2+P2TRQNvfbv5d0y4GNGn6dNj9Xkmv"
    b"XjJ8qt2vbZPJzpzWxceNv/akk4Yr4Wi/cts355DmTFAJmFya9pmbOR+NFpxf3vbwd/5BgPDwoweCprwBoySPOwfc3hEG0yir3ehm"
    b"EY/jdV7K2tWNzKo3Mugxr0O/OIHOg445NKuwqSRF9/fHur4UFlm92ktM6AEM/HQOixWYEfaRR09gdzLl8B+MKQ+X5Ytf9Ot9c1Dm"
    b"q62xrG7EQcF4raaSda1StkUjKBusHoH4YoQvX3RfPctoxC+1tdH4Tl5qJvFJ60TeZvNE6N5xPsTw1WN0xPRNuhncqjOP/snyZts+"
    b"25yf65UFK70WR14ncLoIyerbULdfEBpPqhSaaPMetHCA8oXKdHy/VCqcVvUBdzdHLiy86ZTZ5w6UP+9JcYWklG0Vr9mkAbL1akwm"
    b"T57/JyNfL25urVyZYvx1XufvHw1XV/Dg/o0qR2/usCu9bjynnXcjg9XTM4tR814ytySavNgps0R6DTTkZOiZ1yVSLdvAZxb0Tt7T"
    b"RJzoxj/e5zkhdn8bP7rNn6OWADf6CaKNs786/tzMMiO8OQ6CBMHMUq+VR/Ni5UQGNrX3oEzOQOI5CEHB7oDaXQEfywhnT4cpcPZo"
    b"a5Ju0IW8YBYPvoNV7xLb6Q+UnyyvuejfidbanqxH2qG8u7oEl7HjpDblavdnRDXF5FrlykHphe4cLp/DF+XeTlyd6gdm3LPnZ+6W"
    b"WEnO0gs2fvDdd6ifX91yrnXWC7fiVCrl0rSh/nMEEy5S7lc2H+lNDGtH+dQ5baf/FTvAMJbDzWZR4WoLQJGSqrYSw9u++hoiYqcl"
    b"OBAIkZolSlDxOolFuTe/hYPPXhg97WaltTxhrWD2V7ft4vNj+A3M28ViS2kGC2KHq5fv04S18mmMC/1gfG6sh6mdI/tpU2D+atwr"
    b"CoWpWFB19jicvjTn+rluNbxtLslJ/rTxLaqkje23smsUbxclR5/7xK9x219YmJ3R0zz1h6AxUgivCOCZhgrN7NM/hj45qvj7zmBs"
    b"DYvW8lHlXrubMHo43MO3wkhqr8VvQS1SYDRpWH53sQcjrXK0pkA62gIVjgfLxXO/Ba3FL9glxXslIsq4nxnfSzLssVmeuB6TG7Up"
    b"m8qbmYRaWnk6Cfh7LdsxQtPhOiuRbErbFxLvq+O53vda1Q1Y39mPlOfFTdkauEchwS7QUMoq6q6Wkz9t9wAKmOPwfXgky27SQE4m"
    b"bsS64PpFxlPNyzAfqWag/dXwZ0cXjIO04pBVcEVjYDcA25BrPVsSpK7BxwsLn2HUnRK1bNWd29+GCGjZoZ4dtOP656EadTuCiw3B"
    b"RiXEDbVnvEeD5Y6w+hyP+58WvONkHBS+wMaH4uIBzWfM+DBoSydzWPtMlW9t5G5pjqn3F3BrDnw/zq5/SwkFBOclRalqQDB329DP"
    b"ICSE6BndDq59+tH3MEf1rXZfe76lVcXaEfvi1G1vNp9ub9Iu8NvoIDS3xvz0nO7sRTEB+2vlhZ1rHXFeIJ5LTfYmlS59ysDv5lzS"
    b"RHTgWPziJv4WVo4k/DQfXg+tWx7bkEmHnbfxNRNFlTYOTnZ7QtpPv3xrcJjWkTyuVf8I1Bnk/SWYrGpDx64d8gcrz88HxVNfQY6J"
    b"1EQgqH6Negxnd6jvtyoE/DO0Gm3Wk2JYHtzszpnxmfGkzARpWAyl5Cg50bXgzXtxxBtGZsGMN1WP++Asp3PokTm7mdnwgJxWK833"
    b"6epAMyUCZ+EVXztntvMFqLF02Hf4EZj9Cr7b/UNkA6VEj2fnvJ8+i+2Xh9bJLezwL/wlZmVrGu+bOtn8gNts1rpaWARhdnRuIYvr"
    b"+XT6Po+l93oUDO/lUb2i6dGUWrKXkSxn7RHz9pTODVwiP6UStvFVbDW7okGcjL7qkz103nwDzXVvr++WC1bf6UjXQ4LuHbEcfbX9"
    b"LPdsdR9/Okj5nDiVITjGRdCtHqUx/tR9fLfz8oBu74AmOQz1TH2Lnd/4JXzDiw069zDl6u76KzAp6VE7vl918vYsyDy5T/SMzrSK"
    b"+XQq7pM82sum5Wy7k0kVekyVS/ZX0NmY2qf0XqgTeYmdrCYuPGpEwYMJJ67nEJPBr8/+oMq+y/iPizVbMI3LtNQbfFwPvEp8H4bL"
    b"CqzcdwHYplrEQJ12j4vRvD4giuPkQUbDTnDv3PBMqW27vVLOrXoV8HlHuqIzMivzZR6Fx6eQnWeV32ZC26+AtbVy3TBCz6wKstas"
    b"kiAmzb3SsNUEJAp8OkDmr42Nj51Hj8e4EkY2LFud9VljV6eFg60ZBHbKV/34hR8j+B20nQWsjcuh95yNjyyjViu/ZkJrgW5XXu3W"
    b"IJYWWtaSchkADsRw8EflZ6X3rvTyb4/trqRVFL40Z0SksISBBzsP6axCIZj1HptD42Igkte7ambISFkzkZbTdzk/rz7BNpGDkez8"
    b"nMzhOdOUsCLm+5Cw8yj6VDQq42P7fI+P4Bq3wcTxafINuKq4Ma4HeCnfxo9Wi9+xAjRfiDT6AHx9+Z88t6FG7qFB8g9aNKeLr8D5"
    b"yaA3OVmlXxWG3HG0hfBz5U1K1s1JluJCJVWg8Pc9hHNIvvYBLh61uz3ncd5y9QLFDk9lgcbv95zfKfukJ8M10G29kXpIrrwWNjxe"
    b"xpwcPaBu0e9f0yNBhD9wpsv6FnidjPy+kbbDfXuUVe3+UFjopW/8yXrGiCkOxVuGU2zOQXq3SlT3eawVPSN/z1rSi7Tul6wxp5MP"
    b"c68m7epQllXYZgIqXSNNPu0XrT78EwQwMRMrM+Y2rDr0fBy0fZkADhP1aXf8NQA0Hu5YXm0M79YHks6BqoY99QV7yeQUiJ0K2dIm"
    b"3/tJ3FX2Czo/XVz7m2SP5HhMw6sW4+0+stIuSPeHA9X6nJ9cb6tS9/HSo7rgm7edPC0dFIYdJdKmgjx2lBW/5Be0wc1aaRoAB7zG"
    b"WUNjcD2umvHEVmoEj2MHYqEObsajsF6HsJ00TSKy7YnOBas58qNyRQaK5Vg/kV1xsr60hHnevs12or6lzp/3uBZm07dfPW2X2LBK"
    b"nfKq8JGwtmgq0gCGYU+yViGafQvS1cuaVDqXlo16+mjkDKw2UUTVOtf9QF3+GP45ibT1nJDAaVkjN64EWaGy8AOhB0I41bhxYImA"
    b"8uWOX1+DjoutYy0INlXzCa7W0n4wsGurP6iwbZvTuBtydb3y9J8dgno+d/V2qO9kclE/E79Zo3Ec11eGCmML4dY4f9k2d96oB0+S"
    b"Q72zt8R8sjGsbfFWN58DzuE7VXW7nlelweEfbAiTtvNX/d2EzWy4bVffC4vEmDzBl3HYiyyalJfPmpf/tvTl8m3SWYu23M6Rwns2"
    b"KXWUNsxiQd8EOPlDdMPGSRPNrbM+8vJ7Z1HjdriRvzPwHTSb9R6fSaNTPbLirPfkAatHx/coWCwxTvfTgToG9oRcjH8uvlDiToj6"
    b"iNl/KfLRw9zBY3lmmzG4ip0PRudKaRcGXGXzvjfoieyN1brs+6vVtaiCKGVIMJXfj1bP7zlK796yS3Q0e7p/kRBm323z/iWdp80R"
    b"vyOssWVDQ663plRk03zbrR1m0Vk0iIhgJjH3MOYtGuK6bTVqF86o9E4fLzI9rhtIUsWHwjnnjpP6IrsAd2AY7mde6aXZVu8idOfb"
    b"Yvdy3ojBvOFfDkS74VwXUziIOuvXmSgn6Yfs7fbrHFIGF6zUakGt46JTM1ptM7sa8eg6yHsUIBK3Z3V29cpqzfeHBzyC2sVmvTLK"
    b"C3CafraT+sEqpWqjBVz3yuoX7KRhYxALS8fvdaGDrrWGji90RHXu54298eU2tpJk66Gtxtp3G0JJWezY3NjTl9956UYZIbVqizx+"
    b"VZdvWxz7T1Hlvy5rLnvLQTONt6bcTkrYT3C95E87MzmQZIPf6ne5VbokYdkyDFdypDhOeqJ8M2rmmh9aw2o3Hbzw9+CQVBJr/H5P"
    b"W1JHBY6fRqqewu1gugR8Nx7tnntoMetUX3f36vxF6Qv+/Fvt6FyHpjH6NErB8KsG63bTXKtaVZ/h3KJOfk/0Zwna5G7alyG812/I"
    b"jSLQ+XRECNR2X+f1O2XvTndPHGTsKp4VMH1CqNcYg57QbGwl4NDx4l+6HRs3bOx/Li/knEes8Yjd+44hW+ScVd5rtb/9Jn0ufrHO"
    b"zbis4jPOuM4xnDlc8wz+FQ8O7ep/qdxfLa7QZh/qqx5AhZVWe/J6XnNu27AD+v08/L6VY6L9tcvDe+xVI8QzK8+YUUWquvSkVjdt"
    b"DltWcTGdvuIBVQ0+HvCiabckXO60iX+355PNh8xq3EPDefbWRA+bUdjb0wf6TGnV24X3mbggufp1pAct5LQI+ikAwEpQHE7c5IWq"
    b"THO0ulv7UdOYXN+MU192L0Ok2ps+1UVn6m8Uvx4SHnmroBzbjGLekB3Hr1KvbBeIvmW7h9fGz8eRtum7e92u/drE7jXu45OBwEtu"
    b"FSQ5lDzZ0bC33WrYC7ePo5Yd3tQ/cHQU8P5jSnVhxb95NjdPZ0mVRwb35t5wlNJBIDBr0UNrj5vfhZQseLiRkO3wEmCW/OCnEwGv"
    b"TLLoJ9T8ulkclx+Z3B1q8ZmXHqjOM3Y3tf9gMutqspmWd+0TNGrgIFj0x3grlaPjVID7e7qoj+GsIqUvzg3rWJC821SqSE9MaqVf"
    b"o7w//2R5t9N+bLQ6leQs5PZMWFDv/WGo9itGB7DH6nK1UU6V/eA7YGfiYKryONEcdQjkc4fc9O8c4q4UQ+U9hcqn2SSfT+cKv/mQ"
    b"KQyPPiTVR/Swa95rP8hZ8pn4s/RXeyQY3zZVeHurnYI/tn8hI8OYSI/jjVfAFGNouA0TTYuZ+S3p5mJcFR6/Qdprbu6hGLGmFetD"
    b"EKEOzYKp73TBct/wm0m7lmrZ55+Lr3NLCjdteWDDT9yxPr3zDiNsbkjjNaq/z/SOv306nUd+K/1ho/MtatfjE2J9MFTlwpG2lMsZ"
    b"H1w3bf0kx90K80Se4/V597mRq8sZViKRG3FZ52c+FgemFFxO1aXud+4DGTO2tpN9JV27YAOIH6bLyHTrg60taKJw2Q14Ukm3WLuf"
    b"ToBj0QOKgZkfurvdqF4OO9JiMPCrGitLOFf/EunYxC6osPqnACSduLo/PPCsKRFS2jq003zapvr1r7OJ/aDMFNiwZ2ZxUQUAfLmC"
    b"fYdwOi/zHOPV/YkbPmO08uBQvtcIhs+8Xd8cno8do03ba1sW0e/qTUCL+291vhENKLY6NKtrfWKVrfIqp5TSSfwcpqdKNuZG195d"
    b"ARutMlzvkXcMYE4PuBPXCP2JWIMpWAvI5MzXVTkaTmaYHWYjNUHHJ0rvwvDqEa96eCZJP2yBU/3OkSxXUcdAXsyTpuYpopnRKE7b"
    b"8TwIoG3yuV9OjJ1v0qYLE27feQ27CSJyJAgsj2MoOwzNoZs813J7keJVDitQMwbYUmm/nb3CuE9Xxr/SaHlyOEwt/rpVZzhcubN7"
    b"YgGHL0D3vZwYn5/XEx2vU21bopthMOqGsZ132wdhjaClEri8zI0jXDWHT5GodOeXKRbXNGU81kplaTjkqn81rQ83f+sCzUNj0rm9"
    b"2bdZ1VXXqfb5RI/RYfpKSuN+yGiAXJXGc377KMUqhTZYpjR8rU5Oj06bo6TimBNbqzhquac/MfeBNhaNk9zPO911czrdfC2IWsnB"
    b"b1Qmp0Mc5YaD+cmqGZF2eDw+x/PhWMYejY2y6gUDYwS301EZcK+viLq+r69XVQDpUdNrzZZWfdYYRmdQtwC2dnG6NjJn0PtlkZLz"
    b"ldCdjIBdpWeWf8GuGICXljOtXFlBnTJ9rIPweDlcGDPrRPeqiL6k81ZttwQiVAHoxeUw9k7XTet2W34bM2j4WfvdW3W6j4SieihH"
    b"QrXQA1smSyeoopy9yegW0DPgJ7Sx78Jucz+a+KyjXIfIHu+RhxW16uym76FL7lZCVqk/O0hvP6ozRUX/JI+K3+nsj+fNEqpvz99O"
    b"zA7CYe7fT9mrsuHHouDWzL1ojI8z4tRWL8L89vPOOs8UszRheDIrba7rRl0zAhuuta0rTbEqAFmktjxaqdbWJ2VfmJds/0a+Fg2y"
    b"tDvem8eLesI7gwTtYvgBYurMeaBGBUrke99oq0jJqnbWkBD+zlUs2DkjjJ5Ed/kdUcu0uFjoySdKFRYbEM2XaHwNfPH83A45Cq9P"
    b"96ovTZXTIt/TwLR5v7WLWZJOz+rAw/J5hwtmR+2awYFKncn7adLgQZebIj/aHVXLSMBMxsLnvGFcrCNG6WU4p4bXQ5WJ1YlkYmdD"
    b"ZIltyZxLopS9hi77oSmelhnpUQTN0XSX3MLybpzidrm0YZFe/7QPTu57yx6Ym7p/HCvkb0ufedmweKQzOBGkTE41LZIPnhxvJ6Ca"
    b"pILgfsSwt98AECvmLfbecSrKCWLGftAcvgVNlbYOrby1VN+0lst2GcqrQfZNhMXgtm128OD5ej2k7Petalm/3utu881uwmwffbYE"
    b"1mZdRiY0My/jg/GIVzfisHrIWhTefvTSZ/ne8r6EibhZbycZBnxxhpE/tMc8I+IltCvVq6/mpep+sVen8xFA1JmvfxHoD9z9xRiH"
    b"+mv+7d/RoHRUX1Zt/y7TXNjH5nn1vd621K77Qhrdriu3zL15e08Vb9cK1xyQm1wKwAf0iIZGL7S9+Bzzm+9luNqMItd2UT9Yh73f"
    b"C0wgoK2ousp/Httul+ns+X23b626xQnpLpfLEHv1V0bzXn6522ZZqfsgiKRflFmVzLFJLqgjSbAa7ej8oH43u/2tu1U0Hm3FmyNz"
    b"zMKQwnfD3s/QCqSvg0BEWbpJbJe34d5xuq8e2fjMx+VDd/2YT70Yct9/z6yIk79EXsVndrW9cZq8BFVTtqA3SUeQ/x4ysOg31mvC"
    b"2jQ4g4vUUqfljghwjy2A/prfLWAQVSa3+cVziu2od/gIsbZUzUHcEIH6FmwL6N0SFsvjpZ8s2HgE7tc9AGFMjX9flczYl+6Dvbt7"
    b"zrq3ZkPnlMvUvgEV8YE+TzL3ePEK0pLLv9ZjdAVebx5/LDJpu76br/Ph1SBPK/2DQNE3VXPDoLNZQ1f3Lp981u4HgnZa961RGEgd"
    b"ElGzOhJ2qvtd63Xq4cGwlL+HfvUd97Zpr0puKKHNNKfKT/2CqbhdzeTObfNeHlSj0hWeFCLWOU5Qnqd9azncidM5v1RX8Rdx/2id"
    b"VA/xVRhCB1+vTpff8LnokaticXgF6efbLBz0LEXGbik9kFi+isdutf47whpHW7MGtqkWd2kxVEjf7QrYgvO5iRiKxXDApryrPZd4"
    b"OfB2gs0n36y4k59yySE8Bn7lCpqYtyex+mPqxWSb/iGpMxXDgbvMwO7rnJuNu/n4odupim7f/LGW1ZzmpIqQZ/BhhPcKI1jvdHen"
    b"0J4F5m6No3PzWWfmJgQnyxL3Yq+msx5fvxT7cOBLc7vfvI8BVDk9lr29sIQjViucwdX9S1wve/BrZ83KxeJ2bW+WUfR1n9BmEcfv"
    b"7rxRDeaC0hyMjqR+OpRF03kCjn2fIsXqkMBjfW42FG5p8uwQWL6q3qwkjgakiI35Aji8SF7SaSR+1iqnkVyTZsdfsONoVMdLdL2z"
    b"n1Vak2Sv1zj58pfGehLGN7L5Mk3W0CT0fMgsavzLgtPcOzRN8A6D7LWdtqcZOtmUUOpqNQj3YHNRyVu9eLp0hgvZBQ/DV375oduT"
    b"ZQLLXUqwcVZuGYvBLARyT4kYpFUfGqX+UjJG01mws7tV2v42l97yndx64BxMn5ymzSkvH3kzTqJZmx6h4X04G7X3ULeD6J6WplLD"
    b"6rNC/KPdGJGRzOtpKNap2qDykVuq+A9dH/Wks5l0bgn8teeHeynVWTg59nGBFXhiaL+W+XG4uA3YA2QieAG3qVejJS5Lp6d3xjT6"
    b"mob1vKA2q1Tor6mfPQOY3BTF+TYbBdz1293r+Zp+sFY6vTUidj9eeg8WCj6rslBDL1A6cHu7odT2FEMsVk6ngoa1LTLEk/G17WHj"
    b"vBZIQKAjxkohpnBH8GueGrmMuv/XD2ybagPXjPu8DArs2qmVvvt6U9yQycT7VATeryajpOpuRBvEKIKN3qrdtBFHkewjj2vi0upV"
    b"Y149doDawqLnOYs/lBxfMjBAZfdme/SJ459rhxsdS7L7B52hUhspU+vBRIwstuSPW5hpNpjScf3A9YKCuUrVJKRNWb2Z4JUvd521"
    b"VK4scU6amZgLCeV+v7Ari3chG49VUW0ujn4jD5pU9U19f+n2kPbLRf4w26+oR+CHg9ehkP4S1eysOmKe68sICXlR6syVrVG7V09v"
    b"Dy0RJDC/WZUV28J3OYEMEVvzcht043m4fsuvw6hwRGXRsr2RJ5Y0Pv9JUnhyXUz+TvnBjPxPF7UwdT0llbNQ2gtmf5otUcnL4wqC"
    b"7Qr96cKLeiEkH6A2Ehs+6cCdSm05WZnaJQWae5Mt1ELdbJ0t9dhMo8r5LFSe42BG/oQ2RrFrC75HXsaPZdbilGGX6860bZZZaNPg"
    b"l/oIkkVxGkWXm/2wUDwQGiDKRFsP0o2mJiSv73gfdqOK3L6jRrr3DlQcUoDZ3w2WzpqYZQeCm/7oQVc8MahSud+9zIvOi7Kjd+6t"
    b"9UNGlaB/353e9LqqKoayVyrPEZqXW453lOabNxZLM6XhriSXVZD++JJXal8zM26NZKIIDKQA+fDOXNytcUQ6v6HSFapmx2dZPrSk"
    b"Q7Pyoa5fuXS5xCfNO2oL28qEoMYta7NvKV+F5o0W66vj7dV95gEGVNzWqNTdOHOin2flNwDDgnTNiu4kF+NomjzA1qR1MqD9L9iP"
    b"DKcA76HW6jqaveYxezienPoxvCmGN0qv7rT1ddrICbB0bw/U1YU63ZZWCBxEbA+Ip83bvh+W+6fUgIblG7VfXnOwvl0Fznp1xAbY"
    b"anIqHKv1u8YTwABlltPBZXUxD9QLPH8nmem+z+PWpOjW1hxbtWVr0RwSYC+WBo7HXhJw//aI7xWqKTt6v9itgJUTqayS78ItUPAE"
    b"5/wRV4eIO5PGKSMr9vqXLWQrPPVqH4aNZujMukArL3nuo7HUvufn95PXC2NK0p1mNrPk1fnyF92mw8Lj2/hTydeklut36RlB13IL"
    b"5t/Tlw05f+X7WK/pebTfva2SOHTXwG/Ft/OB2PqjZnhd5e0f3EqBE6cF17v18IMEiUAEC3UNKOXPq2eAW+bDW8wY2Ny8/qX9mcT5"
    b"cXmp6OdmvT3LB0ml8n1firXEiyUfwXFvKwKzfP31ftiiRjUMnCD5scLssUBJUD4QK9SSMJpfFC0vTbrhdzG/RhwU4/oU4O286V5O"
    b"tfl+Xn2gd3vZumWB/N2svEvjzVMhgXbOasd7kvVud81D922mbR6/IlJ2io9ONZ7AuTKiV/MEc4cHvFnbQYcgsLK04pW+71YyrGvD"
    b"c4EMLnpyRqzWWHlWHaTGPL10sjtfo2tD6BqR2MjCLT4Nv5dHhq7o0Yaqi7eqhP4ThkpMnzksbEqdFwo/qfbzw5IbWs4T9g/xN1I5"
    b"ZbyEv+dROoQ6Mys494wFSpeyqu7MNeR0AH1r8xzX2Z64/QhcIAd9bhRQcBHkdZ7MW7S+vDx/E9SbswfXB3da356u/gOuRBswTcfx"
    b"FHHNz/R+/9aI5JVrwh9wTPskrSzp1oHokpAwUbwShq4Rk57AArup7qo7g59aXr7cNfJZyClfN5rCRyto/ZP8608o9WqOLvU4b8Ah"
    b"aHh+dEvr1XtpfgnWIuGMMyI+eVkX7vp61wWn1pLsXtSs4Dy+pKenBYwze7ubPz6Oz8++J36mrRn+5mqv4RsjZ/Q+vuC/oZIU0RoQ"
    b"v+zwU922MxxbilbURZFHDC6N3FLtEAuiQdX2sfnOV6uRhXSip5pnCywbnEu22uvaLzbeIhreEI4eqnSp4+1EgONJZxYO7mVTCjrQ"
    b"P8m/YgL9Pbik+HZ9a4b9ntwujc8Lrbb7lpAUbgHdmQxNKPFab53M4MwIg51Afvm5yMHBNLAo3Dp24hryMCpO7zF6LBfN9bzQXwxL"
    b"yxWT956PYvoPWyyhh1lrdaRb5fl8bBXQpLe2/dlgBtun73cMWE1F9GRr+s3KOeqyVerkt3v7jEac2wCrz/Hh+DVk1GItew1XReI4"
    b"KdgUeKmzc+CiYKGjUC/9Nb/dZ5fReQTcHVakHzXt+VX6Hkl8boxGwHO9OUz3lcEjS7PxM/zjCVAtWfqrvyPo7Yu29xr35q5yzzoM"
    b"K4ZzNZnxXDcNxwA+2aJ/eLdCqsBwBgG/9bZ+R5XzbKLgeU0XB69oedD35V3/yZ0bo+RZzVz8M/0ISSw/saXTFQryFgUFL3Va6616"
    b"fclmaonjLVnF4c+xeE4Xp4csnDRwTFBa75V3t7uSN/71brP7DT0qZHlnkxpjjcz5QKu6xKQ8qoTRq7OH9Pa9WeqNq31EMW/9ewcb"
    b"9EC+W7sQxY7opGy/yhDlbjRMRPRV1EhJuLTerPn32h4VteZeyH7NZn4Fv22+5w+n/6nNBB7pHr0xu5CpP4Jw+/tA29Z8NfaTkTnI"
    b"DuHJTibZeTLfi6XHYRpfT8fkkTHHgGBE7Pb3MplU1BKltPvaBNsZDCYN6PziN8+e+fkJrrth++vDzQskOlNSS7zigxn9a+v8vIGP"
    b"1VNYzjpTc6fuSmrmvL7t766i/CVVfWkMps3F09rO2lvEaCEXFXm3xDOf4NVE5JTsOrRrr5L0/Ary5j7854bTGfPEOS8XY7Ccjxim"
    b"OYcbF0Pocjh0cGfEoAJi2IoY/YHpQbt8Ltrq6DEMj/12MVmYtmcf9i3eJDzVOYXd1chuOudvlzjATP/lu6WxdfV20Y9227MjJorb"
    b"b3Jst9kCd7h9UwRRqPm9U2GyqLObfQlfKFClcQO2q+e4i+jXLud/R1Fow0417m/vq1pMvtLU27lToDNwS0OJAj7EoK9pXaDRP+Ho"
    b"T9PTBzbx8FZ6dMQWaTPHnjSLWmbF7zoF9hzN7da433t6i/HiD/rPLQJh72j9bKSYd0FvDdF+fMAUC3QjgOWRjRsBxV7TsjAbrtNC"
    b"V/KWd9oYnPiboKrnHPYs7bQnTnLUXxwpD9H63TLImXTTmo9QodaQjGhthUS3fvZpRLnMni67DAJvm3cZZCIzbea9A6ul574WmE7C"
    b"02X5tCEdBYZfMgZZ+HHwWwQLkZrzTSLi22DrwqglhzNF0kDtJk00z0X6WOus56v+kcbiJg7UuTPuiGrxLW33ARH0U9LKnV1pzjTu"
    b"pBCvppfyrMR8XUA77LfhvOL7GgmJtd9PQdD+CK601TRobAfrmdnXD10HK23bjfvLEbAE7eNkyFCz+u51Xt7r26ZVebbXaQ1pLIBy"
    b"klZUhkJBZzMlP0QdfuejMDJOA0KeKvxzvtmWeKpe/Hyk95KGU9oO1c2y7lIj7CrgUTV8DVLystCsfe2i02V48vefS8sjup8PAV3H"
    b"9nu8odJHiP4s1VL6idGz+q0eFHgtnQ4262enISx3Ohnow99d/Fz+RmXXndCej+gG8fS+nYFNfPzLASZXS/Dv0cbKwaxdM9E5ebdS"
    b"h7ss3GS/V0sdF7X2A6fz2bMjButUL1e9E5QepXNyDwFgXW7dOB/KjGCUAaeR8FTFn9CmyZcPeMSO/sLILNO1/eAzhT9bLd70yI1r"
    b"NH3hibMCXatOwlX/HkyTc+aSl+q0gcVTGDm1bJ5DkBjRnat96TOdzBwExa4WIhQazdNrCend1R+Q3lpTXPeXTkrdlWfUzxrw0+Vr"
    b"b77N7lSUG1R6cdQ6vIsb24Fr6QpeYcoD/nxXO4Qy01ap0HKwyAcXLiaY7uVouYu5fX4eSmQ4OSwt299g86X+W9q7rqftb1JaE0ZR"
    b"i3REmUXQqkFEwrLrw5vlH5JbWLvGeH61CjsgTXRUKza0iYDXxvBaalTnw2v/YpXn1HU/0zjMVd9TZgIcodKVL5ro97Al/yL5Z9uP"
    b"c8imzqPfzbEgciCuPj7zZdzaeY1umwLtDf34yk8de6xXYVgQsjt43VLOz+binNqSXI113y2Tq2FB2DC8YHh/f7qPN6c8OucRc6o8"
    b"HhtHazV+BJVZDvTaG1PB5YUyj9Oem2Ofszd46vSsv7FXyHEYDTuHM9r2LtfFpovjm5ib2zUykqYPiB2it6ErRBvp792Ni3QZHv3v"
    b"DX/etgvrr3hiVy/+7qq/6YG5IEsQuOf55L7NDV+veHRRTqZl0Xv2584uVg57ZFZ1EsuMFXoSc70GHGo39+9PjktcxXvc9MHsYSl6"
    b"XQaThzQx+6V06G9OItmsMwvyseFZ4+cIxni2nxX6vN4oojLNbcimEIJJRI9fKMAwI484ndEdhF3BJpEt13X5W78gXIPdoa79B8Da"
    b"rXi3NAANKUfYZ488rnT3BWOTjlqF5mCuGlu5Xh3+CCreE8uw/X734jI3XszGkKDBAtbfRsZ1j2J0p90mlpP31DiVZj5T9/QFoDcl"
    b"NKC6UMeoKwt3gGyBw+okxwhVkccsWFJAAEXel8VOKaZN/FaTs98IuoXHiN9++PscTjBHWG/X+XL8kr1LAo+sDXzQ3vvWuRHqMAGP"
    b"rcwI2+XE2hjy8Cg9L1x0FKRAN4eV5OMFgILtcOPY17eMNzarUNCKZ2E0rx/+ny1khZV8ULcefObdVaUJHUNzPpnf7Z29ZSE9AFsz"
    b"tG5cmv2Z7PX8l1H3OgceHk8C+ylWlWXtcByUxnuoZKxm3k1Fegf71OprKJZU26eefgTS31z4QHe6hFX5pM/bIP3jXRmq9Jqr4/rU"
    b"glg7YPk5PoK5PKv0r4jkOmWeorf8Lv06BmdN6PcCs6fWRG7sppd64moEq7W+A8S5rK68NAKF0D0eL63fJYqQvinz0NH219g+HTbX"
    b"4Cmo1N7lFG9lVQet4t69HCMidMH7V21sEJ1y+8h2W4MYOiM3t09P79cPsrltFbmkCDh6qbiFQdLF4SWK1lUA35XQ5X84MOq0t37j"
    b"0q9xVjYtH46zGXK8PJwnRQ2ai/tdWOOLHtk7vkzCwDotSvCqaCuiG49DjTy6o8bIFvtd9s2+d9PQelONtRe+mvgww9wYfmWDKwIx"
    b"zG/JHJfSvNSbvWN3vAsWPbuTntPW+IDNvPOasMssRBfPaGr4bXMxqGugXu8aLX3iqN/xBbeil1eo3O3cIyZTP53vBiN52B+Wmtj0"
    b"4x6qN3xqEBQC/DSoNeaEL/a3RQqUxLdwjSFMh0jqL4Y2p8fY7veMse3M5FbBjhf3EkBt7Ju1GX7ilU2re6RXf9unNtHsRmjJrilW"
    b"udy7Ne+ZZtJSjF+xVh2/Dmj9dxf0tQNrFnJrafPyrt2UuMsfwgvUzdW4OUZqNln1OaSHIDoFhqx1LG0C6Ym6Adwv7/J3fp+52YiN"
    b"pJySG0iphK5g5r1iC1A93rMuT5+9Y8ErlP7DgfZxMxmfIfObxBupG6i6fd3d0XDaZr9QG4ulVva1L63RVBgMtMT/LOzdvhVt6Tcb"
    b"nwPujuyVcWmtpnCgnU23foOGrGYuzXz4AObomG3iziUZ/+pVLoy70n4xvpJP7tN9hxt5WR5/0M/8DJc9FbxMpDMAOGdyPt08d6Wa"
    b"cQseNC684K74XA64N6lHT1Ofa71RVu6OkNodR8zJoDsflM4s6aJSGWXbv77FAtivIc+4W9XW1FV742BS92wVgxX58UdS6p2yC+1v"
    b"++MjWR/21y16vawdujmsVeirS7gR4xb1IXcfw1vIYNb3dOVYQUffzgr/NivxjNmiwhn922Niaws6WxGPS/MZNGucG1EvA15Fa+7p"
    b"nnylq2/0xC/h4P6JHT447aXJrrChFzDVMag7ye9Ip3cs/NH4Dwy84+QQM4lJ45Aj5Xrv6iwBjl2O0d+5ulxKzdF+1e72kYn3bbtb"
    b"Zj85ljtgMePckTouwPA6YSgbCsD59VG7CK5YLZ0GiJpgh10+5YI/jMsfm6dlZcQXeb07bMc8sKN0HS90M3x5fcL5/oZK7OCVPvWt"
    b"dYtFcnu505J4iSGRePmAOw58pIesTa95nEpIuVE8s9Ze8bQoQXrdEbcChQZCnOeX7okVdiR+V3tpWjWMZkzY0DdcV8d0H0zWy8Zv"
    b"2j2S8NgqL/KRKK/feQbmu2ACO3d7DGJRLpaXTHvROktIf97uNNBON35fEeqBoW3nMCju/GE2doVB3O1+6v7yYXjzpqeNV6zXmrxA"
    b"CZC2EhhXwx8T4bq8PfEf3PYd+WOXq+8no7dRgW9JffflpMCWyotHp0Y24oji73CFug5CtM47xjDZJ5VnVIPW3zNj+7Vi4DkniLyk"
    b"0zay1rkClxdP//16M4X0841ZXg/vFt2FGiUSfW2VMOs598UJr/WBoD657YTz/IHQ2+Q1O9IXaTrlP3yigGrC4vjc5IN+abCGhnld"
    b"wPXWNqtY3bA+RLZl5GLY+eiauEKfvcg/d4Gi18d6F+GoAMOW5PgBK0l/GSFk3Y6Ji4vTDbAhVelJy01jrpcvFedLVnZdHiSNI753"
    b"v34bE5ZsCla/8vzvYDg3PtqIUiXMGL23d3D9PrcHXvkHOVeb6qv5le0zfX3T2r1Xmc9fD3o0YadfD6w1xleKMOekO64s5NUB6Qbf"
    b"GFXoXm/fICmEXvfO0frMXf39Q23qGboYQ5sTi42IQfHcvHXEhTulf3drbptgabFseSm1tBMMWx4v8avRGVlY8yYjV4gcseOhmtx1"
    b"z9zSy2e2DS7aUQbe8n7mLg/MHJ8nFaGYIMD+vhKn1BGs3ccPf9I8nOx141Ojb7119YctYtX/zLbV/6zcG0U+KoZW35lupvPhghof"
    b"EtuXJ+p8/ZoZ+FELTn/nLH9u/grSV7TBuS33NkNTbTFlvp+FpVc3sXtlQH73MLcosA/FN9QzIrPsvxVfQoDeDXd3iOUq7du3DCox"
    b"qlJrGaNTVq47I8rp1i5w8i1xl+GmqyOb7n0y2552N0SbeXKL2psxAjD49ewPH9WdW52G0mLEhdTnWbsuFCE5iqNfR7oKVdGsfG5j"
    b"hhGlBEPp3zcJXvv6Ix4WdtaxJnuKv9bBsXPJBs3ziMXvDp1IQI8bD6rVVg6PqjPdMw55pKFW1KQn64cmN8oEM4uTWbt6rumk8wv2"
    b"eLLvgvIEexE35sSbLrJyQ2nZp6x6fqwY2GZamxVGg8iXyRpwZXReeTTPzigFBiVWDu7bppEUT0LotGbiwGqy8davb700t+bWAifX"
    b"pjvZ74HfztlMNxDsD0wcTwDw6ogLlg+RBVE5Vh4rGICa74FdcXQiq67aihrij8Z0lx9bBj75cLUsewXL7cHC390Zgqjd1a1BVVPI"
    b"RvrcDKD+eElSti4ltPNDTFdBPkV8P87PBuJ1++zj+ZqEf8SidJADRrqaUGbXXjtqjTJQR0RLT8ohMfSjp7ukkp+QziMb+157fhDC"
    b"wFRzPuz2aDrsdfb3Zycrt9DAvn6ev7AwXtf+3l7x2+3cVszLAiRRwDXu8+uCbbeUeHy4rdQXOKPI8aoKXVBK3lVRaT20bkNp6woY"
    b"5pdzCgsex7rUpbN4yL6ncz4kK2t1pi9uxEDulMJf56yW8+N3p7Kwa14UeK7s4IXxbCvvzcIond4SjYsQeO7W+prY8ltTust+BRpB"
    b"u6q3C/w2Z8Voe5xXLbDevCyBbAGfJ4zDVCq8yoH1LMe2Njjd/wYVAjtihxAWflQXou/LzRarXAkiJeRW68CSe7he2SWzab3bq1q9"
    b"511At9ZzhVGPipkEfUHo1/SmMHgzZti4BffKSAlpLY/79fZsFhwfh8q80r+lv6sh6egI8chs9FXKU0N+T15AMT4yu/F6rilFWdY3"
    b"qt5DFadqwxQgPa+MCDxqX4SGRn9Yp95e/dEf+XEuxeimHw44qAO8viej+3zEO3yDqcuzMvsjYL91gZTbh1vL7TFkeom7bn/rfVEv"
    b"JuXl2kFTJF8staN08ZtXghpgJ2of5eu1A3mnmjeAmsb274st6Fu38iD384N7NgdhZcD6ET7y8+f01kSw4Fb+8ases+qJ8+w6HFHy"
    b"lgFaxZfnWCTE4LywzMa1CN+tSRM0QEBAaDyY8uoFMUSoMrGldDAZTd4YepS95I4JG0d1YwnunBekeTNLjQP7B6EV/DIv/zZ+Bue9"
    b"Kk2bIe2ZvYre2Fa48apOKqwhAteqcnE5fvWSV1+qG2bo0uhvta7I7zmMG4NN+law26m/6WiJJLyqBFvW75u7olz6dKuOCWjSsU+m"
    b"Mwd/mV0+T0Y+emJKw/DW7t8EQIzq1QvbUVNDGu4FonHc+N/rqLq9RUPH0aLXVRx86PILsv9OyaG9GA31FkUR7fenhCScxlmJuuQO"
    b"+fwistVGZXw1APm3y5kHYTbJgG/lRB1tuNE+tmcb+XU0jZqhPsgRqDyocBUNS7UCyXzaftvslmwTJycIQwVwEUs0er2RrBTzCYTR"
    b"tNBv45HTO9UOhDkr2hk/fQPhPw1qLlnk7CqeLw1TvgKnQeMNlNrPa2v9sfcXgFYqTXia1NtTQcyLoabgxhMnszNitc8lvV2EYtUq"
    b"PzlRsdftOZmDK11kGrml8n91dii6EF/J0F8ErleseQcv+nxnbh+l8sG/SuvJySc2xNv6Lo7q0Zqh3B8DJayaN1aLt9nGd7tb9jhG"
    b"cnYI4c5jp1c67ixeVBqerwV4t/b2bpMpWzkXEz8hXkeSDf4x/G16znfzqxaz77gRqafz3X1/EOnUwpZBuxFCtzPTcQNNXaa8K7ZK"
    b"c5vW1/U/unHi+EQ9aMTpuEoul8leJS7ULrI6tLkTR5+vcvmWp8l1eSN+Fx0lxFBoXNkSJLpSXRf4RAQuqDk+Lt0uxMpCILOT2HuP"
    b"N6rAvsRq1hI6YtsNEpOKzfYgnQ/zHde45tniOjkWbedBXrDmjikKQyis6Zn+i9YW9xu/lMmRqEpdIp3V5QLGsdGk1Tdhd9u9pgHN"
    b"tqPmjO0XebZMoUxYzjWxjCHp/bucqvbIY7CUPNGcT3jUXKzNnxoCr8KSfZLnAZinleh7aG0/ifnzjdHPJNZtr85nyZZbRAYx9cbK"
    b"csPZdDEpUVOg0a70+pN90M7NJB8uz4LPD7oYyALtQ6qSY2l6qvJXvQNc1+M+kPWlISNIROvqc7tdd7KZOdwlLP9WpmYTtTG6Tt2r"
    b"VL451BYkIwWJBoshCDeJO7XI6apopbmAn+z7/tAN5F6K/BH9TVv4njtVHfNlqWS4ffI2aL6IVj86l9gV8tG/w7jWVBp3H99fZj/j"
    b"ndWq14dvR7J5BWCimGCDQzMfYoL5VmcVmTni47JPHs5MvZarNbR30L574g4hlbvCP5v8yW0e4uqrBHWjjztezBfqQqZsPcX8PQSV"
    b"1aA1Pbdn9C8xVbPjgGxlWUVJw+Ji593+V21t3e8s5rLeaZRZoF/WMpwEqCk3BJp7eHSM8FnNcz7aJJzSE7jzbPBTkTh9lE5/HXwr"
    b"NTCpO3tzuFSER21Ery/9HxOh+4Ew39P0QXeXHMREp2x7urVe7FnF2zBV/bCHlJ9r1/vaWmpz5iN/O3W89ZjCtcRs6R+bAjagt93y"
    b"+Juj4qtf3s9wfVd/1NPdpRUYke1jevZrJoSNi/iHnUvVwyh4TEs+P4GcpD7zen8A4G7P16ySPe1BmzweFjCq0z5lPmA+Ogad8jm1"
    b"9oEiGm2zCkCzfXLEd+UlPHK0rQf0Qt4YpIDKEJNF9GP4ou2eEj3E6xYczGt3uXUfVI5yeYOj8ji7gbpx2l6W0bEsZN2R8ArpDVVu"
    b"u8/GXjBmN/YVWdfWsuP5J9Z97y5KRzJJA2rUiJCYNUb2kTauH+7yS7ev/Xb4JTdmlTLLgioBJnvfoY3DSdaWRTQTrO+u9Dq9Rvo8"
    b"G7JCcX2+wPYrMuRXz5qYBd7+g8+7bFsw72b8dRcOkjP3h/OQbo+TuXbKMvaWdsAv2BFsmjGnAzGR+0O6OnhqrWdlOT7eKpcX2gCh"
    b"gT8EMUe5P4MRycLjfeMrgDpO+q3qSMTAKWdLAjop+wdWk43FOSSGEyVoer3l/U5ORtEMl2vdz68Kw1jjMLPG+WR2ysnZDvXXWszJ"
    b"SEEn71FvyDkV+TF8Nu9t9pLWy+Ak31ml+LGBemVehIalW3fT4BZDfL7bbSC0MZN4WUOzWzSZDYbl3mPcU04T5de7PZezU3frLINR"
    b"MFps3z26PjsE66ITOYOJ8dg4ppo5j52q79bVOFl05v5nYNQCsrQYMl6x9vHCoZfUsxZf9rw1pmbfSPbGTqhBd0nfZqv/Efem7ZEc"
    b"VaLw9/4VOcVjXOWWRMaSm4bmjnrDfmYMjA1cGFldT67d5ZaqRFVJXQ3Yjwcu2IANM+8YGPZ9GV5sM3dmLsYY+C+XVnf7k//Ce86J"
    b"iMzITSovzCu7parMEyfinDhbbCcevXltPzeB9Hj/Q+5fr248em3oulcv7bNsdenvP/6xv37yb48vfvLv993F4hHuull6+cFzo3Pn"
    b"0v14sXAef1RsU+EsL5zxeDKdLMfj4SLfLzacLF7GF5LBYKQg8GdSOJPFZLpYxtM0HyLAhrNYzi0IwgXPnQv0ZyufprMsHw6OlsVm"
    b"OBiVcFjF1lhDJreXeTyfx7cJJTTOtAiitXiZW+2xaqowbOWrZT7NmoWzyfV8saTCVrH3OJduxJ86mh3eft/V2fT6oxPn3ldfOfnx"
    b"5+9+91cnf/rCyas/d9L57cPl7Po8Prxx+83Xv3PnT9+79/Vv3XvtFecjt5c3ZlPkmXPyne+/8cwzf37mczZrbsSLG/kCOORMZ0vn"
    b"Q7Np7sTTDB/Hy+V8qF5vOANAMGiyjNoKrFBAWw/DH11gC8CHo1EH+JZmD7JvMaz40QCe58uj+dSUKSbTeH/y6XxYAVm9UENTAiQg"
    b"Ffv5FGDgt2Kz85AT1hGcBwyDJ1ahO+h87roDKDMcer6zaaF5wPGl/t0upqrdWs7Gqm0hMC+ZXLfEaHIMjdp1V4EIXeb7VzccdyUj"
    b"Ji/yixF+ZgGXkl8O8PPlnXDH9V13o8YdB97sRP5V4V68RCV8wUS4s4Ofr4jw8pUr8jJ+vuhevehekVf2qmaCjM1n+4IPjzecaaND"
    b"NdOHw2Pn/e+Ht85nHfj4gQ84Q8GBAdPRaOS8F9Be1T9l4WI2d2YF6NnUmcfT6/nQ3ajYtYF8qleU7M/Sm1rbdqHgNhY+D3B7NbBb"
    b"yKfJFPp/PjvQ7KSiu5PtCcDLPcNbasGkVr8vNxw5qiNEqCcrKOYDWNhoG/6soOJbu08Czczfc67pzxF+VMxTDwTUz7xRq/itrfjw"
    b"EJV7uCpLrAjU/srFqIGPIcJgVFbo79X5Xa/pFkP2AKRpITKkSaLfZAEYv2TDScEybTj5hgMm6vqGcwMwTY5PY1WrC/Fn+SSUAzmO"
    b"Ll2SHovQnDzpvB945uT7ixzf7IRBdDncaZVcLLDxivah+gMNY3wEROTwTz1aPrkBCB9wBG8IHnKpAycHnIjZcFWhbAGCrF1wYoBK"
    b"4F/abPUwhqoSkn38lNKnhD61MF2/DphywFLAv+stTDmUKqj88OkcKbjeRrFcIieGJP8Z/EMqzkPfQrf2KFtVEukdQhvOQweeJ8rP"
    b"oyCcVTCj/gcpQAMKnxSz4HsEugo8gya1ytwgOQFpyaHMdVMGvjMsBII0xOYYxsNnxFb/zoLRKQ1TRpEU5nYdjEQR9OU2SuOnIWSf"
    b"gOkadsvxyJJ2bc0gGNh6cjaZDleVTZY1u7FCxJNj8MKr5eQACdyPD5IsduJt6DmQAjCGDIkBQ3vRtG2EvU0S4oL7GJWyQ7Dnzmk7"
    b"O5weHUC0cWNSLLX+0GfngQsg1OeUa/9IPodWHDjLGzkYTXg5ny3j5WQ2PVezyYAJkStcKFP4oLTN6nGTwaoZ++FwtQ00Ljecm/R3"
    b"5Gx+AP+qFqGLVG5xAZ9uAobhFI3RqF7/imqnmldULwItTJVFYWieo2+J94+gU9LZ0dTQTZ8tuvdnaN0JEBErKlQBeq/efOADF9RD"
    b"69lnL2Bh68F7LzSFSjeaXpftOrVVvuxslS/fnVad0brr+XJ8EyJnDJ6G8GEDrW6m2whSi89rISd4Lfvd7rbge9h5+e3aY8G3hY8v"
    b"EF1N/PHDbJ7l8wsP7k+Wy/38wTpC4W8bhCo2JSuFaLDvma963aUf6HsCIXMEgKgCjATFwHMdKAHINQUDD8kbZqwq+zT8VrKkfs7Z"
    b"3MKAUjdutKWjZLA8Ga9rtSJmoDVwcQjfxxQyLIYH+WIRXwcBoO/jBcSTFzACmOefOprM8/FhnGWT6fULH50f5Zr1MNrI50sKZXRp"
    b"DPuq8s4F6GQHTAjGzg08duN3dWkdt2BQ0Q5Y7FrsRoJJI2IA7XgOUpehqAwhJr+pW9lAZXvqhhdvOvHF7mSP4gfoafWxo6pxOptS"
    b"dag603e9TsAJX3XF1JH8IF7OJ6vhEoZIuvBgMHAuzabH0BsLcFvM30RIh5QBLdkMHsqVdFTJLSpQ64D9CcgLIixDx1FPF1CtKnSk"
    b"Jq1mcy1f6HKs9jxGqLE50/yWY7Xn1mR5g6x5vp8f5FNoMeB4MM+2mq2q9HkCqvCkatCGYh46OqpQi7KijKuWqC/dvKnYYBhT41ab"
    b"N1UrFkcHGvWGs7tX1jxZgRxOr+/nIAn7RwdTbNfEGCcMpXbdPehJICHeZeUnXn4S+ImgjypopV+m5AVAdM0h9ztsoRtpWNYF26jQ"
    b"wPIu2EaTDKzogtUPnSOLC4p8GG6erQRtpi2QaQrXZHo8XgOfi1JozWPoUmei7e0sZL+ir81pxT3t5VpwrMG5UbP7jpp9dNzsiKMm"
    b"t4+Vfe9p8blzi3Eyw4FY8uCDKoDbJfjkwSdWV3eeWAWXYXwePrHyLz6xii49sfKiJ1YXxRMrCd9dCd+vPrES8OyyC38BTkKZiMG/"
    b"6MGNEpELL/3gidWO/8SKw+cICl31ABiQhxwqAYQc3l25AojgHcMK4XsIz4WwEIVQ2IWHDGq8Ci24jH+h0A7+g5p3sHUA4wHSS4DA"
    b"BZirAB/Ac+5ZiCQUCKCWi0CCAMAdJA1awwAJh5ZG8D6E95cBwUV4LuC9D4iuwF9pk8aAjEtAr4BaGTT9MgBchIIeIL0MyH34fgkQ"
    b"XALELrRCApJL8F5AuR2btCtIN9R6FQpFWBhIuAqFXWwp8gg7AN6F8O8yVHgFEEpA4sFfn9vMBmCBLUE+wecQWweFOPILWhIAwivY"
    b"EdCKq/B+BzsCvjOAd5mFSEABDoWvwksfkQBfODISSQFEV7D3oIU7UNlF+BfBdw/Jx3LSQhRgTwBAADVdQZmBmkJAdAXlBFoRQsGL"
    b"+BlJAZgAeCkB3gNYeclC5AHwDmD3gQQfAEKsCRkKgC60jgESF1sAiC7B+x1AtIM8Q7kKbR5BLQK7G15eBB5cRkmHz5cA2WVAdAX+"
    b"XcRC0PIAeQmfJVTO4Lu4YgskIIqwFqjZg88XoWAA/yQg5SiEQGYIhTyA4YCEwbur8MxHubOZzaHZEUorIPKxZShoKD9Q6xUUPCi0"
    b"A58j+BwBkksAK6ACD1t70ZYjZCAiQXVAwYOaL6EQYiF4dxWe+Sis8HcHWwl/JeomIrLlyEMkUKuHAogMhb8uCh08vwgkRYAsREVG"
    b"XiGZiACtAIqHb6sIPAzh4UWsHVUDBRE/w/OLSDZKOooHfObw9xJ8v4LMBjjp2qRdUg+xt1ApsZtRfiLT7VxJOZoNqaUezQ5aCnfH"
    b"QnQ5VEJ5UYs+igMaNpRylKdA9yqShNKOHYA9iMpeE0g0Gyi5aF+uXFR2CDsAeYNMdXUPIqkoBihzyFcUXPeqhQjNA0opqgcyE+0T"
    b"KicpMFd8QktAfAuUtUAF5mh+bETIXDRkKC8oAiiUaBFQ14RQUo0yhBKOJhhFBBVXXEE7bgukVAJ3hStHgJKLwoaGPtAWAB0DGj5U"
    b"EzR6O0Ip89XLtq4FSrNRSdHAofKiaqAKoCSjoUNhRLuNZgSNGhp/tGG+zWw0XmiP0T6jI9jRGo8mFz0LSjcafpQxlHoUUjS1aJNc"
    b"W47Q3aAKoElFE4HeBK0fehBUWLTNqO3o49CKoglBG45uq+bX0LWgdKOiSlcZLDSvaCXRjru+cgqoZ2i30EqghKM3uWqrCJpQNCU+"
    b"V+4IzS7aHU87RHSa6JrQ86LLQvtNKoPiYZtaVEg0oehN0Vugd0B7RN5CKJ+HlgDdNFoFNDtoBNG9X7JbhAoYaFuNbgh9GdoktAKC"
    b"KRtNnjhUTgBdFvp/tElhjUdMmQQMFC5r64duGk0LWkv0quhZ0Laj5qPXQTOMNuySbdjQJaOpcJkyJ+jbKYAIleVEt4NeA60nOge0"
    b"RRQbeA2XjcYc3TMac3TJ6McwtEE3jtYQoxB0mhj6YICBdgk9LtpvyRu6hi3AgiiApHc7ShzQzKIkoyIz3fXklZnxfbZAXlZygQKI"
    b"Ek6yclnZJDT0aGKQ8ahGqPUopEQeuidbsjESw64lRl9VyolajqqDJgQVGBmMakNelytyXVIXu/t9JXAkP5dUryHfLmlVQF6gDiLT"
    b"yV5dUoxGFakJJJoIjMSwR9ApYjyE1pBrL4uWEMWDYkumbDXabNKAWsTGlOCh1qO1RJVAiUb7jHKEpoN6a0dZTuNtQpJy27AJ7SGu"
    b"anVxlRVAW820MKJKXBFK1tCsoJCiTfJsRKgeKCeooCi96JLQ2KPnQEOPhg0VFt0QWgM0M2h6UUV4TSB9lFDlPdCskt0JteW8orwM"
    b"Wk4UTpJ6V5lb1P6LO41AC+0R6g7Zbqkl/bIyaFe1e0I9Q/eEjhOdKfk5u/vRI6DhCnXkj+YUPS16D3Q5qDZou9GjkNH3lDpRrGC7"
    b"I7TNaPDRMqJLQt+F2o92GU0Mabr2KqF23+jm0WXVolrUeNL+K8pXobfAmBJdN5phNDNog9DAoR0ib+sr+yQuNfwaxoYYylzUBg4t"
    b"Ifp+tJxk7ANlPdHbos9Hm45m5YpNGo0puPIW6KZ97cLRBaHhR8+LHgYDDPR1GEBgXIAO1bVbhPaHgvVAmVT0FmjQIh1UoNm9quNs"
    b"NMPkviLllT27RchcrmUF1YGYzBR/UDFRPEItHigOaG6QTDQ1vq20qIRopEhxXdVLQkuz1JJ9Rfs9NC1o21HeyE4FFiJUB65VAI0W"
    b"RbZc+baLgSbPU3KFYoHWMdBR7o5t2FwdJ2LvoHFD6UUFRbFAaUZ3hFYT/Z7UQwnsILQWtcgfNTvUkStKNdolGqu5ylSgZUSDhgYO"
    b"3TT2FmoDicyVhhfB3kKjL30llGgZaRAslHCieqAFRbvE9OAGDSDnjWEWdi/aavQiqHPoRdAOoSigkKKtJtliylKSxXDRdtu9FmmL"
    b"p+0NmhNUUtQ7Gn7qEaOvIzk0eOh10BjWDBuKPVo9NPYUfPpKyyM9XkPLgF5mR/t9NIKo5OiqmO2y0UygA9jRY3oKiyPl78giXNax"
    b"pa9sOzoCCu5p/G+T5in3glqORgyNHNpm1DMat+nh+WUzjNChMTrISzaP0OFJPXJES4hOEa0fRSMXldlA14OmF50imhB0U2h2PVsg"
    b"0TVHWjnRkGHkhk6A6WEEuaDLys+hVcSxCpphdKy1GBKdInoLNPxcj5LQamJwQXGkq8dol5StQpOCpgatgLRJE3qEjX5fmojD04G7"
    b"p7wFxgfoONHcoAW9elkNJVzeGGahTQ70eIQmDi4qv4ahDprcSA8K0R6hwfMvKsvKxIN7o3PncI6snFgqJz6ZiysUenvRzpXHxx8X"
    b"Qz1nNsfpb1ya3GUbjrvh8A1a9sdvQj3Ab/BXPeD6nYHcq5DwDiycvkE5thYWWrFZEB54FQG4hH8AiH8EAQcbTkhofNxwgAvgGw7+"
    b"canG1rqujcfrwyNqaBg7HU9go8HG9eHxzmjP+nTtnevbDxbnizEtqN28MZ9NZ4vmXqxbwFK9lGNAnPc6AtdlzddNZ1i92ZSN7WC6"
    b"ApzYVp/O1d8bYaO/u4063/9+J9zeqxewJbT83FOwXvIgXizzuW6N2hKVrw5jvWDU3MaGKzs02Z/mC7ORyqy8NNA1iiqFoI8k2I3G"
    b"7bWgeQ2ct+DrBUjIqxJK5rvLUIdbNDa2zZEk0DLrQu24SmOXe1mW4t6okIss9aSPn9NIctcLBX3mUci5V+x1oKEuKXH20n1ws2Zd"
    b"qiLda5WjekH49ZAjz9UfVqtQBzc3apJXK33erlfwUYWFlvMWtNRfW6mz1y9ou0x9tW6SoRxK3AU3qTYFmJ+boH03QSdvgjLeFNT2"
    b"XSgB1kt9wLVO+wu3vwir480+TdI9XFRtbza66bq4vmx1Bm5C0GS9F5eYcT250rndm2yvjYQZwdIwvAOGN2BEB4xowLgdMNhebLXe"
    b"H1HbaaeaDd3F60wouSNp+d0FkvQjYH6jsSWsR7CsBst6YGk7wE1eg3V7YAOCFTZs1Npfc3BTUfA3C9y1kh7kyxuzrNTOxdEB7csc"
    b"NjbCKiNVl9UesRSsUyYntd2ctJGFBIT2FKIQonxI3KfA61AoAgD6WcdAkpQCnN4DUgKiHAD0ZyucJMK0oQHx1ndJTVEkoEwdXOyh"
    b"rRYIvsl4o70SS4hGCUkVMCzRaI+H4LIB7lUVML8O7yO814D3Cd5DeNFgTIDwfgM+qPhYbz30IC7kAcehoBJxy9zgW8HwNWsKTOkj"
    b"uyXGXhhVm7XRyG13bfxtbb9eR3pu3lT7Wswa9FlS9R7ncD6ZLoc3N+oCs1FjEwnQpu/RtpebJEzN7c8VsLtnC6p6AKWFUHsFoYXQ"
    b"RdJsrKKe6sXFmrjqLdFN6SvNm6U5lfbKhjyk2tGPQTQxCMLAghIFiI8Wz14ksolEEpKoxHEeuo1EsBeF10ThKZ62mtHPSr+JwicU"
    b"3EZBisN6UQRNFAGiYDzo61k0CraX1tveAUEV4eRT2t1vnSjYwO2KlVgf7scgoflqWTqlmtU9V9t2TaFQJfqH8/x4Mjta1HcAoxKV"
    b"WNUGKlSp2n6q8n1DwVa1cKWBZaOscNS5I5yarwlWJYarDsiF2WFN3+oAFkX09lzT6Zj9BArTyDplUXmlBe05v5Gvhg/GnKdcJK6X"
    b"JDIOBcsES5IsyZjgQeoVoYwilqSxyIMszAouc48XXpgEceqzgufug3YNypYMFpPrUwzeBmTdtrCeUetsg4rCO81hh03d3WTbe7iJ"
    b"uEt2NCuVBHV1XNmyxHXdgQXTbBu9GKPlzpujhgpvxfL2TjILwUbHUGTX3cZt/eXQYdTZRAZNrO2IsrCOTJP7XAKOsZub0pTWJOM2"
    b"tk5ngG0Q67ShXQlu1AWW3FqzFvlWa6EwGkJo1g6hGw3o6Y461+0NTUYOaw2vny54y92NDldu13u8W3rORAVo2qa0l3fWmavctq/p"
    b"5PBGPkcxRivbOsFlbQkFG0yM9s+9BQtbE8qqrh4bWwE0z16ldSur69B80RRprW/WMmpKGyGrMSpLD06zulnaa3Kblb0F6/sXso11"
    b"g1hnTbPLuzvaeq873ACpN93m0Cp1rtfO1rhuY2vpdl0XbNB+ZahqrXqq14R21t5nQ9XE5WYzuG7r/5kN7TIAdfGsS5ppP4f2T94S"
    b"CWdYx+auzBqytWxpB624Y/pc2wvQxF7lCfqr6qNerkt9d9Wlp+uuua9W7y3z/G0IRCsAONWk1wmo5h3qPaP0HMxj2tioPunfqP4e"
    b"JzWGJtWHcWp72F1sJX5g5gM3H2hQRJ9SADNPU4CsPnPrc20G25IL3WyrYcmiaaoXo3UJOmNjvr05H0yZnt6k6VelpBBcPmk3tCHE"
    b"7caamVxrocXvbS28qrdH1Ww3Yg8bNjn3/wszTuFDpU1tFrybrbDmG/VDe+pcy6MSRiWJWgxLVTKyWD1gzQe8+UC0evy/k1prAcRQ"
    b"/BYIbtLbJLdJrSIWCcVzeJcm8/RoP54/jiKO0z/JZGmIxY/OBfXnATORRhNL8HXInYceKudsjiBkQiUY0tifcLRg5vniaB9H7wqY"
    b"ppDKo31DKjOqH8dTJfTGf4plLk+OJ1k+1KPs9MbR9KZpbYleR6V6vQtDGxUQOu97ny7Rcw6hhq5CaeLB7jPaoCtY0/aQzjyN9Nc9"
    b"+/BZYw2kk7qrw09sOJ/ccP6hpEafSPyE817nk/p47SdwTuUfzJGVD55W5B+oyCfxnOPT/zAyRR7uKfIJ55rzSfj3DxrukR44hAHg"
    b"z2qkjYNsRMfV2qHVR8kfLZtdlACv2tI3jOHx1aEujKekH4V/eE5pMTrXz7oPfvAdVvnBnip7a3z44XdY48NvtcZHHnmHNT7yVmvE"
    b"2bWDzLOXNNIbOZ7WOzqgA/Hc5dyV3O1SptoKG0WjDzi8Y8lrmR8cotWoMKsJzGtVXTV4uwVq/hHP61jFwfhYh+bxuPIaFXpvrcLP"
    b"NipkjZnS6uW1C62Dni0AbFHHm/e2i1YvP3tBr5o0qmLqqKrdqRVZ5x7/OFcLxHEQ50XOXVwIDpiMCpbRArEMcpnGLqXkyKPECwuf"
    b"PkciibjMclo49pnM3MLDzyKMi9zNC/yc8CSJs0CUmx0ABZfwk9J6c5SJOE+jBD9nRZAIqIo+hwnzM0lNKcI4FSwJqVl+EsWRS/CC"
    b"ZaEQOVUfeaJIc19a1QhPeJEXEzrpu1HKhCrmR9xzXUIXpn7mwlf87GWFl7KAKGNpkRQeJ/gwlkUcFNQUxoARwsutakIWiSIKqZoA"
    b"OBgGQqjW+XEiM8WQlLtpkVJ+k9jPQik9BROzEJpCK/JBFOapDGKiBhD5CQ+tanw/lUURUX94LGC+lIQiy3iRKsISz4/8LCYCkiRP"
    b"RJwqwlJPZKCSBC6474Yp8SzgQZREeWrVUkgWQjOo54ogCyKRKZ4JnqYyYkRAEvhxzgh1BNXkgId4E8YuE4oRXpJH0G303CsiNw68"
    b"WtdEie+L1FXd4QciVbsPgjTihcekkowgi2SmhI7nYRbFsUIX5FEeR4rfSSY9j5oFxOeul8VWNdKNuecLTtVA78ZRTK1OYpCzLKTq"
    b"pSd56KtNEaLwMpkHoYIPksDLCJwVuYwLaknsxQn3Y6EjJTCEaA+PxfBgcV0frh8fQ4Vq30b5BFo4veDWjt1fKKHLFAIUnaj0OHsQ"
    b"L+gV2YYJreUiWRyrVUiVeAAUGb5WlWrnCKPDOcU/1nYIBEeZy92CF4lJC7DRgkjDxONe4PZD5EnKizDN+iGClLkyi8SGnUtAx9WG"
    b"F8OSGecdf2RvGoAIq7PtDGRPhr5/SstCLwr9RJ4CAUhAIfJT2s4yBoIoG23H3zsYbSNrsbdgvFyxk15fLF8z/drwkl5fKl9z/dow"
    b"kl5fLl8Lg1xzUfENZwFVYpkEPl1UvIRPl9RoBT5dPmevLIF47m6bDEOPmsWhetSMw9Nz5dgTNwro3UfbzN+rXvDqBfMx9UL1SlSv"
    b"BN+WofVKVq+k2fX1Hucx2glSUtQMEtW4k6mRDOgfiLurJ/YyBZ5tVDl9SnAa6OAWOYBneyPFv8RPwNhnSckqKK2qUQjK0jQsYqo2"
    b"bkoXoZswsA4ly6+W8SghKEsLLM1V3cIcsj6FNFmRJtcgzbNI8zT8acT4FjG+hj+t+YHV/GCN5odV88M1mh9ZzY/WaD5zrfYzdw0C"
    b"GLMogC9nk8B4RQN8XkO8hC1fYh0ypE2GXIcMzybDM0s7SEdzWKOK6OkNTxXwLTIAvoMMPfsRKfjAIgLgO4jQkyPom7FAaNHwwQ92"
    b"0cC1KriqQGT1RB8FsqKAu2tQ4FUUcLYGBb5FAedrUBBYFHCxBgWhRYFcg4LIosBbgwKtD5oEfw0StD5oGoI1aFD6oIkI1xEkYVER"
    b"rUOFtKgQ7jpUeBYVgtnq0BxzqyJCqYOuwtZqgO+gQminwVQBW6mhQAcVQuuDrwrYOv3ww11ECK0PQhXwrJ7oI0FaJPhrkODZJARr"
    b"kODbJIRrkBDYJERrkBBWJEh3DRIiiwTJ1iBBa4SiQfI1aNAaoYiQYg0ilEZoKuQ6siRsMrx1yJA2Gf46ZHg2GYGtEs1JIVVEKpXQ"
    b"VdiKDfAdZEitEkrppK3YUKCDCqlVQpkOz9brRx7pIkJqlVB88mxn3UeCrEjw+BokeBYJnliDBN8mQa5BQmCT4K1BQmiR4K9BQmST"
    b"EKxBglYJTUO4Bg1aJTQR0RpEKJVQVPjuOrIkLDJ8tg4Z0iLD5+uQ4Vlk+MKoBA7UhjswsIxraw/ONRxb7urt3zhcG14EoKQLSO8n"
    b"x0Hb8BIApV1AeiSEQ7fhZdyL1gVk9v1Xc7Pl8mA5+NzpPikBKC/2vrnU++Zy37kLux3nL5QTu3q2tyeznDWFqAD1IsxqNh8mwPnE"
    b"zPAmokYcLbcwvdLRmNIw76yFXqHmNRKmZnITbjYsm7RdosodODkeNrYqdeBXWZYbk8/vdVjH5DMl4wSUeuv3NXxwjR68//04OXHN"
    b"zPieMp9MOJ4eaixBhaWaLFb4GB81ciPDr9ryiUU17qBCqjEP4LhgYvipo3x+e7w4AC+QzLLb2H+q0zac5cJ8qh/+ojo022iyXrgR"
    b"DzecEtWoBYbcraPvhjFVatGaHI+P6VDCkEjCBMAPwSCIjZAlkRIS6KD0hma3AtkkeCz5kNqyrPbW6z4zBWqdZmSC3o1dVbyk2yKt"
    b"n0uqgny/VgXrq4K9a1Xwvio4cfTt4LdFcR5PFrlzZZXmh5hTdTiYznQF284As+YuQWvpu1kJfEdM1Fnxli7TJ85kHISemmhNROoW"
    b"maB529QLU88P9emzOBaJmiouvDiIs4ImbCNfpDzPtOXF1iBSxL1LTbMnENW7oQI6X55dPK8OkpRTieUcYxt21JF7E+rSCyN5kviy"
    b"iAs15xxnaUpNTAvBwiChx7nLmAgL+uxnblKk6rMXCxfoown3RLI484WaX5YsdHO1qFFwIfLEL+oHQnHiOfZCmdLcdJqmws3SQK3H"
    b"ZCxL1LR35nm+J9QaTODGITRTTYcHMhAp42om3y9cHlJdPHWDoHBpKj2LAWOcuc16iyQJ/cKneosslWnhUhf6YRi73KVJ8dwP/NSP"
    b"fbWKAlSJkFYKWCzSMHPVmlCah4nr03Mf6skztXATux7nAQua9QJ5LNZLAZyHXpYEmsZEZpmqKxB+Efqeao/nu8JV7fRZkOZcweSS"
    b"A3sDakMs3ZyppRJPyly6gjerDcOsKBIeq2UvP2VxrpYGUukHsWKbl3CRJIQmZ0AGTTzjSkIsslT1YpwLEchMHaMEdkDnqTWjwOVF"
    b"4CUtLud+FgtfSYCbAJclfZa5W2APqCUakDamOM791BNQnZKYJAUw1QbpeYEXEqdkzL2gyDLVKyCdPG6RGyduIhKlfCLzsiJRCy6y"
    b"YK7whV4mChKPq8UXCWwrCqY4m4Awi4zq8tMYpYS4zEOpVTgUYZAWcbNSr0gENNLfK1VLnLHO4TYy52MRe7EDtbO+2tGhwupQnLW2"
    b"QEfXAvXyMM5qIYo+5rPI86y8WwGUv4jVOpGSMuKOicJP2fFDnryxMURhRPzUcP1hb7Th1NMQm/IUO0zdai91nCkOHNeWjCyz1lxS"
    b"ah3g7VgDipNYFmlYrV6NNsqXPugDKFtgv2xh8EGpith1OzEI6RYe48UpGKJQCldGaKtaCITreq4MqnWeLgQ8DCTjHi+XmGwMnHlc"
    b"MsF9ab20l6D0nurSv+EYoObgcFPEovyIUnO+eUrGcd3W/8yJzemXbFIKexWM4rYjOTo1XlUg1um/ier/hmCpmJJ2EpstetXlEJrI"
    b"CWoClNfDnea+jNrGjGwCYg6/pCoy0Sf+zEfrnor5GMDUXQZDKsWkznuvvnLaQoGf1QaOWkFeFaRMB1ZJae6LoC90JNS1dsFrYlwc"
    b"ZKlGRXj4R7VG/eUWdLlxf+LWbEQbIztnAk0dvF5wPEunx3jlg4qQ3DGOeCrd2lAhCnJpg2wVDnZVBguV40Lll/BppYFTLgfPigjL"
    b"6uTbro72BlA9qhJBlXBTs+yqTbz92iKqwacapMpGQfW7VLnfVRt/R7QFpjaVGcM1hIkeTrJ3yklVp6dykqge6+ek+w7ERGEOTJYQ"
    b"blip6av2uHUeGm+ocljbp7hs2QUakEET0ZKct5wDJjaua0dtBuBBMCYP1luClGENuDy8QXUx35y7UDujqimFZTlzoKca1ple0HML"
    b"i1vxIXB5uJhDpAe/kKXIPODTMk7283Gh91sA15a3Dy/gNU6aCRDhlpZXHWy+QU80lt3tvbNYCBiUzYUiZnEOt2JfK3FMtB9BJLTZ"
    b"3zKrrt0Z8zFWPXfdITSC9u/iX6b/cv1X6L9S//X0X1//DfZINjTlIxs9s9C/HbSmWT3ouYX+7aA1zepBLyz0bwetaVYPemmhfzto"
    b"TbN60HsW+reD1jSrB71voX87aE2zetAHFvq3g9Y06zT0+Ocaqu2u0hIMKqq9jzAKdXBckYFW4xgKt9zg5jncgZgFtMtSNSnTTcp0"
    b"kzLdpEw3KdNNynSTMiLpXE2hKQUB0nt6rRuksx0kqTYYHKeUR/yomBUOtZ0kc2MZRonwktgPwjysYeYl5lOwYq2ok03MIsm9JCii"
    b"tMik9D1ZwyxKzKdgxVpRHXvoliWOU8ojftS5HhxeieOU8ogfFasHh1/iOKU84kft6cERlDhOKY/4UXgtHCWSd2bIlVaUIqK6U7Fe"
    b"MU+RrwjAJpTRKbg5vLQQPZ21GXCeKsnWIl65KPNl18p1g1+ZgQ5saGagWR2aG2jfhuYGmtehhYH2bGhhoEUdWhpoaUObL7uyDu0Z"
    b"aGFDm4rgQw3aN9DchjZE7Pp16MBAMxvaMAhNSXuatcZ5AoUOarKP1diHALyHv54BED0slQZA9nBRGACvh3HcAPg9vGIGoEl5i0+u"
    b"gXRrKzQAU5tRZu9oRllPKIduGEdpEKk5syAKXTXLl8RZEURquzNOOWdCzb6GPAulCNPmJHJjDrl7/rg+d6xg8CatkoC02mNb5iZs"
    b"TAw8+KDrOW6AswEud1xJMwO+4wr64JmHjJ4AmDpcrcuU78oC6rd67hu8niojqZgC8gmIEYTb+T+0rGe3p1l8CbfLT8CTcO9cjYd9"
    b"k+2+aPRYEOd57GW45TrN1FxwUBQyTPI0kYUn3VBtWHcDLlPXD1w/STK18ZoVOU1PMilywcOsNqmIU81cCJa5blzIgqlVgzQuioBh"
    b"jhKWByyJ1eZ1EXo5cyUPPM6ZmnAtXJZnvpfJWEpWJA3UcQbl0zDkYRq6OZXwuQy8jPFC5q5f5KrRmZtwEWaxhAe8nNvk5ZiDsZ6p"
    b"TcZqU5u8nNkcknDu6XGi7iIYK2FegNrwb935qnIeM3TN+Lz3/z2zKgzKW5+x0i2gGamwd9KqDlW3j10TVxqexqghjVGVqNWHm9oG"
    b"Y4NSGjuv+9t0iHLbeq3SmKOxfqzMkh61wkgTh3prDzhH9gyiPcykKTkykdJkyLDIwAooLqAPwnzg5gMzH1zzITAffPPB06dBG23W"
    b"NzyfPkpG4DNmFVDYOo9wBZj4oJH84NC0AHq5fvdvbWBvpiSmlPRro/zMrM/c+kz+7lCx41Dx6fCQ4qjDmuOa4pyCPHfurHPVNB1C"
    b"ty+piRG6i87igpnMeNdnMDDEnGOch1EexngY4WF8h9EdxnYYXC6tjjouD4tgPikjqSFq49ylo2m+OTSqriak+VVJ+bm4K90qUFw6"
    b"H7Dnpig9FQ3DztW+6hrmaNEBgcnKRZv9h/AbZ2+DEntnUVxekW5kDhHQYYAh/MaEgdHpRdGG+UxKU1RSUZr35ez0ojipFbLIJEqY"
    b"e1TUoyljcXpRDwXA5dI1ZX0q62PZkIp6XmdJ7AcAg9KchyWraJAbnFUsoBl0Ifz6ydXVuXNm4X/cH0soR1+QW1ehROS4IXn8mJx+"
    b"QjFA5rg5ef+UwoCCHob0VRXhVsSRm4IxFVSBhQokAlMkpuchoWIEnBk8ZXFOpSShDQlMhR8xYcgIFRTJFQ2ZqbswhRUZKWGJqLBr"
    b"WhNb9fmmSNkmFeKogoIK5qYyxSlVRNBzboj0DCWxVTxWTSS0KsiShEEYyhWpSp7wU2EawalwYBicEahqiiDUKcErYjxTJDWdUBCk"
    b"KkhLR4g2IvjQ6kDFkZhQCQJmBk9ZPKVS0vBemNa7pltU0Kn7gZneKai8Qp1TeW64q+LJ1PAsJLDUFPFKrhCkNFIRGE6HpvrU0JkR"
    b"BmbC1MDgKYsrajPTPz797xp5CUz3qlATIUIqqapJDGrFDIVd9b5ndZRSlcIE1LmhTVhcjAhtZrooNEUUg1XjSmFTeMri3GgpMzxV"
    b"cuVbjHMNDSoat0ZLb2P7z7a14q13UzmbuOANMYlf35A1JR8C7/XuKrBJ+llYT2a6dM1WnhDGWgVXB3XzxJMwClPneyF+5746JZpJ"
    b"N028XO0UCAvPi3KpYzDKO4vYzMCruXdnuu7GnekZu3ZaS/7eKUv+YfeSvzrEqg7bqgPBUaYIpGEJDTPVVpYi3DtzFea/cSvAu7GW"
    b"HbvGLLgmAtfZYUl8cA+kFTNVJ2BV5FkdgW34M0wJuq0zi8r2IdVmyGQvnynMSbzI7XUzmkXecFYQU62guhU8WkH/rKB3VtBzK+i3"
    b"FYSgqwhhTDiVmfP623ud8SIhtZP4FMVCRchQO66XnavlW84muxqC8pxa08wk8MNhtruiuRj4K2l9DT7gkUR6YucAn5ar4Qiw4XC/"
    b"XA7XD1jjgZXPoGxl2Rg9DC9TM9PuGfXWrlRqa3DeIbWaor5MUWqgDm+vS73KXMy6JRivC9dqGj5gUfOBtXpPmZnVC8UPf0+lMVGP"
    b"Pmse0bvAyuOmUjRj1Da1kg7OsBt2V1Zq7kytE6hVArVGoFYI1PqAWh1QawN6FouGV+sWs+oBuTI5oKFRctTeuKvhQgKb9UGZXH1l"
    b"EKhHp1AIp3irrc49g1clr9f3Z0m879Rh6htnS8StyeNWxaYugNJGa2QNp8sFblNit7QOTOpVVWy0aedq1Nro2pwLICyr7ZWZAajZ"
    b"QV1Go1MMGR/HlJuNlq+3Ed/I2fyAMmfb1l30ZH0VVLmPWF9yX1u2NxfXD+kSd1/iXmTWt1lfYbp1YwK80An50Vlc7UsSNNToCQjl"
    b"HSdkRo3KP/CBC+Cp2oWttlvXVi/qiVnwHmGbGSplU8UX+Lutj13ffeknJ69/zTmcz5az5Khw7r3+jXs//Mf7v/hfJ899683Xvw2v"
    b"7379N3defeHkC8/dfe5Xd7/x0slzv7n73S/d+/XPT7722/vPf/7kO//55uvf0cju/+lbJ6/8znk0z44W8RZden/vpS+dfO2V+5//"
    b"w8lPf3Hnta86/KGHBHPufft/OdhGwZ2Tl7559+X/Ovnjc288+8L9n//jn5/53Gn9ZfLQ6E57P0YHZR9+AC+hx+n4+vtrzvBp13CG"
    b"CB0Xk3w/G9JvzSDNrJ0pXpEymcLjxXLeFKKyJnASQ1QaGO0PgLn4CyfNtuDX1Rga0BbxRN81DigQPe4TGSgODFqwRppVA3VaexAT"
    b"DM7MO9XFFXc28GDJqLMKX75bVZS53O0qiv1ZvFy7Bm+k9pofpcutwzi9ORy8vwDuERJdT7sK6gK7ivhWGaNZwkHbcCrSl1D/9VYp"
    b"3OeuymB67VmWDwdHy2IzHHThOMgXi/h6vk7V7b32H8fXV+Y4k1sMjqY3p7Nb00rRFFuUqH0G/zxVnzHq4R+3ewgnWqFBI3wGf20R"
    b"V8VA5/cni+Xu8ugQ7TIKOkk4MAEizIZ0V5KqEtO2dUWridKQEQVM7eeoHKpyo3OKz+N5DsHoYjnsqVe3u9qWivmpGZ6cNIpi7fbE"
    b"vKt4gqzrFe5Fi6TAxERdryEo9EI/8jjDjWsNiL1Gm7P8eJLmQ/Vn23kUrDAI1S7wjzjZ4qEivLa7FslQ5bfAbw8HGYPKrHqJFhsg"
    b"ne3v5+mSUnnWQWs02kXiSaYglcwjUtmolT6Pm3A1ttjwizzVxI+Xs5v5tInebzTg8HB8DKH9ZDbtqyCol0ji5RKGJk1ehJ1QvI8P"
    b"USf4+EYe7y9vNHGjwHRBpzcw4M/66mCNDpzmy1uz+c0mR1ijG5ef7uMEa/TeftxiL2t0X3p41Nu8Rs9BJDDbP1q2egIgG522yNJ4"
    b"rshWRryGNugCHh8t8noJgGz02UF+MNMd24E26gLmDZS80VM4TutByFkbtKuVvNE9s8VZAssb3ZTMJ9dvLKfgEloK3OitY8ycnPd1"
    b"GG902LLCB66a8PlNCF4HsZAFTVDRwhY2QWQvtkbvHC2SJq2i0TU3bp3FR8GafITAsCmbotE9ycyIZhfGRs+A58ggoBhPY8N1C7Hs"
    b"hlXPemvwuksdxNOjIk7BYeXzVk2NXrsBFNyK5/11NPpFhwgibLJcup2A0u2QsL0Ol9rpjfPp8RD+vX2fBoWN+TrC0d9y0hR58mwl"
    b"mG41P8WlNWFFE5/XhvH68PkWbKeEkksqQQ4n/Q4AyGgEBGUxI0YOxEKfeQoRmJixafFb8Y1hZIVsnh/O5ssSmVZXm691fTWR0BkY"
    b"KCd4D3GEQp6JAmk/DYO3FhmL01D4Z6LQPe73YNnr5b60+nmNSIV1iBnzWtGE3wHl98pQ2AHd0nT0ji2oqNeRuB3q5bZ0kHVAsXdi"
    b"Og5ofK+GP4s1DMhpAb5ComOB+PokpYapAZ+2IDZIrec6bYgNXTkay5g26lyMUSJOjYtt+J44msTXhtsHqOnitIA7qBfolUuKiW3I"
    b"RXbTQMIYYd6HP+ot1RUX26Cr62NchRiXvVD2R90m2mW6rD9rdIdai6BViOVijJkL+pDLroKLA9EQDlTU1uiyzwg0OuisAQ4L2gTy"
    b"07S71vsQJixutklUGt7DE0rl0CSyru12ycPFzT6B4Q3FSuP9/fHy9mF/SCo2aoGBXRi+n+XeeKO/jJWRrYY1OmEGIfVkGu93yHA5"
    b"En9yAXJulq5oAUhP01Gkj1TRXJ3zWZrG1vPkZILgaTlvN50tqUBrnqqal5sAY8BVTnG8r7ZOLeej5swPvumfOGqhsNdj60iqQiUd"
    b"NOUEdgBsR4zjt/ch6X/twPB0vsiXFz720atQWxMXwmxlRweH5uofMDsQnY7jRTqZXKDZSFxUPIzn8XI2X1wYDjYGwOztwahvAqw+"
    b"k4V1HM33NSidRe0sp9mJQrw/SbZop1R8iy5CySbXSTO3KKv/0HQsYNUyZ6aquz1J2Y26iqo1eh4PgoX9GFg+OI+UPYAusHr2AN/B"
    b"pw8NTLW4eILcAMuvL4UDhEP4R2K04ah3HY0xQXivy1OzbPQsm6TL6u1eIwk7vh2qeqolY7qdu5xe1lVtTZb5wWJYz1aDF0hNTNKd"
    b"erIZ9WwXIGhFGLFZqWl0WRSzyo85OE0/yPDT6UgJpo7WvIEhrN7TOUQ7uYW/hqNRDWY8X07Sm/myCxL3x7quO2p08xbdATYc/A/o"
    b"QTbCTZXnHfiCM6CW8Oilj41aFqIxOLF5KrW9MOlv8tv6cxmi0BLOdm01C2dMh/p2p3Jz3ZN9myARpGIXgg2fxKV1tRKGLaY7Vp0H"
    b"6JoJvJdrD5NBQbFq06+B1fv7dp/Um9RRvct6O1aeqmxGVcumWb6y5CifHh3koPp58+LhCW0OqfZXXL1a2xlo2tSmbNWCv91suFoN"
    b"uvOn7919/h/VAtPJD16799qfcNnnsUvSOfnav975w7+8+fq37//pW288+/zJ1351/+dfvPedbziPQ41vvv78nVdfuPPaT+++8GN4"
    b"8OSeWRJqsOp2Y3ltl0gv5dPsttsd3oZG3zaN3utLWwUBBHrTfIxLZc2FxHLBrFqwHBaDzygoN0yeGuxub2/S2rwVK9P9atdn8+uz"
    b"6RAdmPZb5PK1sdG7V/QiFMpsPDVLUnX/VjeFxh/i6mzdQeIHq+xoa392C40urfzCO7VApr1e6w5h23xTO42tB29hzPjudpn4EIuf"
    b"b+5ONE0hQFMtNZaqTgZPuOq/QR1J9Rw3IfmB5wrmylFvNjPNu/p7leigfrP2Yjh0V3IHl8hcLQa0eQdHnJrl5UZP81LSXh//Eh3A"
    b"NkDq9ahxV41taqyb907XRm20mmvOdCLbXOouaTNEuZQpRy3NK2b70L3giWjLcqUF6vpjDEjMN+f9ZH90taondAl3r1eThk8P63pR"
    b"VXhNtRiXV7lbb5lZpIUeXYXyiZUrsUc1E6vu4vXuHELvjHrfmlR0dK+a0djZ3Je1ZW7aSdShtiq3/AMXTIKZ8h6cktcqp3uN30Nf"
    b"Opv6RUlg/aeh6zfAxc4Ww7pSI9HjqpFoz+u6bHq+AsRoG7/NDmgRHa0N5Q8y1da2qlGJXiVJBqHvc61ppMBQxNZyxFLpttEc2nNs"
    b"FgLB0mEYsu3y1VOD0iAoAYfnFK5Q+VHNj+42tnUg2t1t3NBRNlBJ3q3ZXM0vdhWYbE/0NpCKrPYhGpw+DjW6YjJfLDHmTWd0YQCh"
    b"px096hOr16oecvv8PylNhX7FeVNRcYuWlj9Vz4Z9JXcJMtSfzqtG9QhRb7FrqilnFCMCavtDeKsp18rmau74rAVD98n01kK92ldL"
    b"k+XqvWb41uHscGhiOxpPoERpJXlqk3lh6EaC83CTRLUcXoysfZrMB1U0y90QPumrRxHd+XK3JoDuYSgJf9VxtqPl4VHXXh3sZL0/"
    b"zhYig5/uP6g6HK9Lau/bBEC9i25bo2pIaWVUcdnoNARYskJCKTTaWM4WTLsuvYdKG/JreHKrQORaCAgMRXZ0hmxZ9KtCgEvjwMck"
    b"R2eg0L1w/gIh6j4ThAYesZ9yYsjsTogXuS+3El/aY8Be86cqH+FFwEqkzBhwqmcx9aRkNfzDgcXbGgKqoMtsIaq5gI5ITo0V9bjE"
    b"/rN3VoCnwozuAI9iKTvAa2z57Q3VOsI0Yqe5p7LcKXyhO+yqdRUFjmraoDGCU0EJDuEmNMCrtbXaqnzBefxRndG04Zoa02U2ZOWY"
    b"OnY6J4PpbArtq2MrB8F6X5AZdDdmem2hWOMdPR0MRuaqQjNXi6uTXRXZ7zvwNV4Pgi22JbZwAm9Uo+IAiN8/hRB6308LTQ/qdpcJ"
    b"WU9jjFrG7cVnXlcImzOuXbjbs7IYCw0GNUrXQdQDWsenNjhpOs8OuKyFzjY8pfhi3C0xQ1MWSrTakJjnCWDNjAftnLzz2nfUXsi7"
    b"//qKGjTfe+mPJ//0wsnL37/31d/cefUlGD2ffOe1k5e/fe+rr5z8+PNvPPvs3R/+9uSZ19WAGUrde/GXd5/77f2X/3jyU3j17P1X"
    b"vmiGzmo5bUx3dbKAhwJcLvN94dXeKro6J3EUD+HtZ0q7jhuZtnF0VN+wtI1Jq2hD0rajYs8Ne7Zpu1K6agK53e3bfX1tFbJXTKCu"
    b"v5rODvP5wV9hfWZz0bazGdJP9YxbDytcjY1D25h8q7U/yMZmNgGpipfguqHiCt/y0/hmZzGJ3/c4lr4RTzZCbBnu9YE3n74xvvQh"
    b"/I4be7YdafNC7crZxsODW1xGkQgjX4ZSBN6GU9uGA630trzQiyI3cr3Ah5618OhtOAC0Jf1AyoiFIRdc4kaYcttN11urh3HbjWoI"
    b"CzyAEUK4Lt6KZm2zgdZzei1ZIFmEBxotFNY2m+22llpv24ak9pLMiN1h1WYcaABKod50AxTBuB5nJLcrsacHvPbE6quFaMFK+wke"
    b"hIWnuBlmm04825tetmv2t9ZCNIDbyo6iNM1Ut9bAnfrelV5kjV0r2/1W3t6gok7eZDXGde5kqVpZblqpHlX7UoC3TKF6Sl/Idlw3"
    b"CfZWkG3bXlZosBeY9IVgIoqsdpVbPqrXflXKg8e4n9PS92NXbrn+Fv4Wm8nR9WKysjXwkIxNZYdLK1Qy2QLW2w22nc8MdNstm0hL"
    b"U7iDAjqfk7nL8DNHg6+3NWzj9u9qfwJ8farXUNn+3GamWher81OtiG/j3NiqCJ5Y5eEYPsRPrLJA/0v/Gn75Dz2xSsPD/wm/8SUL"
    b"bUZUNaNN00JZeT40BuUaeGmyLRvQabode4EbSlWDONTVswjWdq6+jG136ebB/ia0bT5TsZS9dr3tmJlBC1d9xXq7OZdkDyZ0nwGQ"
    b"OVJZoelYoN5+mxn2W1hxYXe7inF3t2mY1+H4Wh7P0WvPXS22F5q31UGEziXl7WbkjJZnYXNVBcgW6mrRGNUeBR9XgrdR6dtqy9Fg"
    b"PviZQXoAHcn8IAg48zfwK7e/H03H0E4WBhE4Cle6G4PjQ6gc/t7M6E+Bf4UfcI+FEbizwSF834QC3AvAOwUbg+w2FAA6B9mMSizB"
    b"By/nR/lTD9rKZLacdO1YGdUO0b697jWLTAer2XwMkcBbWWdSbcretZWcw9ligsvFtKBDMwQPOXS0jIeNnHo4estv75oCexu1ryoN"
    b"X1lC5XvYD4d6b7/EgVVG5/syVgdDqOHTGa8m0K38vgrRMMNZsKxcbCI01SFWzZPdTUXApsPU9HOF0+5WDW13wlvpADPh2ug+a+5+"
    b"P14sx8V+fN3MZe1uUhYs/Vln68JCbgmhp9HNF2p+hed8+aJGkHrI9qqJf5VEy66Ue8R6A9pRntKFDcvP5wFXVfOmaicdwzS9SScb"
    b"Kcsyr0/dd8wyoWjqqf7NWgpqfVF2hdQsNnCDvP6YiBmab6Ix/1iCCcU6wn6+9a6DeuLShUbf2N3QZixy8TxmbjHs2N7rXMJQK93N"
    b"OaP//tmicq0gnU2LyfWxXtvCqIB9UhwfT59YxdETqzCT8ERABJA8sXK9Tz+xirJdiBrkwC5Md7VgWVbAO/bEEgpDOcYfAwxQuMAv"
    b"IYQVOZTPERF8h7Ai8tV3ppcTMF+T1ZIQXiUZhidQ1gXYPIV4BMqm8CKHWCWS74EP8MLlClEWPvA3UCZ9YqAqTJKnoSm5CnUYlE6w"
    b"Rqa+x9CCEP7FULjwBtX4vZ0SQU0hdU7y2T1Wdo9iuZVjoZpc04mCwUWsPUuwOlgflvZ86HUc3JcC38k7Dw1vN6rKVYmDyYqgtdXT"
    b"HCgNl3l9SgAEgk9QNfjKE9ETtZo9Os0kEJx9jZIqaGacL6hEBk+rku91dP5CosbMJJaknTKXqC6nTyY0A135aFRmPNo+UseM1Sla"
    b"FtLd9oyOkBtJqEGGdS6h2AqPFicPTmkI3vJlmtELoXCetygs15RMdTtXHh9/XAwrHa7iiS29hKjYulGpam0KsTV/O9BpAOn/InDy"
    b"0PEKp4gxTy7+nzoicTLf4bGThk7gOl7gpIXjM4eZfVsmBKd0ZOWS37CxWKGh9GqcrK3GXauo6GZOe7kO9zLK0RkT+1XDalzdVh4O"
    b"9930rhYr4WzO+qezeT5eTFbXZ9k73e9VM9838jjL56fvCqs2hOHZS/V7u4wi9PY/GtUrbGbb/XSZT5ebenLWfnVJv/poc97WbFbo"
    b"tz8jE4aixMGoqWEXle3s2SRn+FUyRxsyna6lZ/pQB2xjszJgb9+qKh71joM1ej3v0THG2o8zGsW0pKh/k0glHvZQfX79aLE2nvIC"
    b"vS5UauMP4GpuBTLbNC2WWL5Hd5/thCykaoeBjbS+5wC6eFSbA0T3h+BW9NLb8es4RHuQhU6q0VGrTdMTqht3dc+gwVhtVt1o3pon"
    b"e/ZgftP0goFS3xWOkq3mpX5Qx1DyyUDpBwpHyRbzVj/Ys6nTy2lW6kokdxeKLxabi+VRQhsZz1ics3YKjZX2EsNIisFnm7W7betY"
    b"esdmUK33ei/oUx1It44OMxwaUhvLA/S1CcKjeDBqpqQwxXcHR4t8vhmDlKj9mdb04i6W3OuiBHmxXG5mrSL6GMF4uRzDS2Wc2vvu"
    b"DJqNuinSxlpPgShHqH1mn4mtG9ft1treeJmvlhpH6xiH5hbu297f74OvXg+q/AS0p7ysBnoNH1SQzXwAD8+m168fzT6yf3R9MlV5"
    b"AQb3Xn/t5Df/fO+1H9/9/ncrXO+zWvPGF16494eX64vgnzl7em5CTyo8+KiiofamhczMXA8ey7ODibV+o5YQ4QX3XE889lEZXLLe"
    b"6rmi2ssW7sa08+ATk3im6qitFAyYP6ime83keLX2aSu7FrPtjm4z72oz4B1zbu2S7YXDUZuYtTD1rkTaCI/QGu185CPjj+0YG6TU"
    b"4MbkZj5XTmLYG6nUx4iDweDuf/32jX998f4vvnjv6887N65/5Mbq7wnDCDOv3HvpS3d+/1u1rPjm698++eoP7v7wt3e/8vrdr/5M"
    b"LSWe/OO3nY899nc6F8ybrz9XHSl33nj2edzF+xDu7r339W+dvPTNN7734zdf/9Kfn/ncQK/jQzNpoXF3r2dvu17kaW1tp4Jmi9Hg"
    b"gcWFBxYDvDe3Kl03I4P36miVCkKUp3MBTbJ8pmR1fOwN1ddJpsO9dS0JPir5eew5d/+fl+6++MeTr33j7n8BS74dOyc/+MHJP73g"
    b"HO7Ht/P5+ygB9vVPTw7VJlsYURhv57zPMf6IPipfY1Zmucv9TcY2uXSgR+7+11fufuVPJ8/95t53f3D3lz86+f5XgPtvfO/7J194"
    b"4f5//u6N73zRAWouBIErvdBlERMB5y5zOYeOe/ijH/0ILkpAJVxyJjCzzv0vf67eN9pAo43rMrD9EVhjQRdn+I1STmfH+f4cbLmt"
    b"sXqRZBBIUVfXtkpLrdLOABdap8rCHE+OZ2OsbezLDjMCXF+CYB0gqLVQ0LBEH/ngRzd3PsTcDvNSa5NynuOetncZWfB91UM79JjU"
    b"gSybi6FHjIs5g1uTQlu8RvMXCxi40LPBKVYZWaOXkq8fUXYaXE/WNMaHE/wumI0BjO6kyBfLfgqtpBHIHTd0H+LSJcZlCqMMXRvl"
    b"jRmgixN6Fc8PfLl5HMYEPo8hHBs3euLwRnN1YXZwuD/Bk1K0bYDCvQHVN8WFnENo6Gwa74/nEFgfHOSK8hpRSvHGi9l4fxab19AB"
    b"wAPFUYhqs/EinedkmAem+U9pI3Ubi6GQw3Dg0yoCpgXALF/GEwyJr+eWxLiVGOznxySjrH6AufUzyCYLSlKWTa5fN5sj9IGs8p2y"
    b"TvN8HwUwmc1wR8FH50f5mbiB8jSfKuYSJ0reobwptGAO8VYvRcE6WKn8waEEHBBIWs2F8HAM0qVrMs/PwIaFIKwEJo6z6cLCplpn"
    b"6TDmXn6qhW5Aw/ixMeAQOxxSDzHXxeWmXfNi76mnys1u9RNxupff8aE4zFSlJunAwm+h7ILCLGiOaVQOhcyACj5bsT7N5CHfEsCB"
    b"/ujj3vgjf7fzySuPjcHHmuOQG7qKM1ja/uk5SKUnLqsRx+BjGODvUIC/7Vht2AG6zVzCFSSdkmbB8BUoHbS7ZCfFC6RJ6xsHFfVC"
    b"7aZlZXkHAhoy6MO6m8uY6lpecP96esEdPGW32hrSGHYqqkCf4utD9MnKG99/5bd3//1z5BkfWDgT9ae0ziaIMMKy0Wecuwx7ddTj"
    b"cDZd0K4v1XLc1LxYDu1u1228UI5qcBR4QXerg90zO1peELWN0Abxlp7owUGEyRTXJPPkX144ee1Fh9w8ELifTy88kDknX3oBfL5y"
    b"9RcemBOpJVZlWcna27ubcefxNpQqyZvNluVQ1hQusdQuNhgSrJ2UQaXmaZyfRagNE2Lp0yaUvtIaObXOyhrwdcZNVozn3P36b+6+"
    b"8PKdV1+792+vmUOs0yXNM9FpXWym6f1y7KYg2rkvj/CIol1SWZuRff7SarmC72q73QwF1dEQC2mtQXQmU5XablkEg3WKIw0Ioue6"
    b"FVvKlAxHo7OotNljpLHcP0ov9dbTisutLiaw0/rYFgeDvuNMdVkvmW201osKftQjMBbCtys1NXkxWVfxXK5VOf58TOD6dbVwc+5j"
    b"vnQ6T0qUp5KW+8PVhjPVTbqJXYUrIKx+9GiFCxI36cjRCk8gDYdQ0yY+QVi1Mx8qr846rYcUMBmkeIbpLKS+tNHW8UwtPHQWaqoR"
    b"+FIj2M8FLxO6msIrVUfPaoCpepqNKQ+BGQAed52QoPlrEEX8ROfPetH2HBc4hla7K+bqH8rgSXlCV6F5RIJ7fO4c+MRHdz74yKX2"
    b"IgvPZCKLNJZR4LkZhMxF4sU5Tzn3szT1fKgSCv/dI5eufOjxK1B84EvfF0EQyQG+uPrIlb+7zHHzhWAcHzz+yAc/NP7bK59s15Rw"
    b"kfJYBm7M3Yy5XpaKIkylFGER8oDnmfQzPw2josjSLM8yDyJ1Pwoz7ueRDKNMteTxix/+RAu3Gsp6gkdukUe5xwrB/AK+BDIOclfI"
    b"TPhBEMo4kRHHC5pcJrw0S33BU8F5kYkkd3Plmgbc5zKWLMjTLGIei4Oi8GXhu4Fw4zAoIim9PPXjLOZF6HsZ54kf+alkYVjg1U6Z"
    b"RlOIIAk8ICKJRFT4ScqL3A9DAb+SNEwDvKKJJbGbZIkbplEYsMRz0yhmfiL93DQmDiFq5W4SyySMmczdIi2Y9MMsSfLC9eJI5PAr"
    b"C7K0cP0wCn2gixVZFBVelvMwiDWe0E29SGZxHCcsSnweREWSQY8HmMqe5wn3PC+Vnp+LKA9CEYWeCAOZ88IFVsWpPs46SHwZSJ6F"
    b"aczcXCZBlEYeVBQmoRRpLrEPZezH2JsejLMilkY8DxIBRGQsZ4Y3GeNxEQPrmc/CIhaZ7xUR8wNgAy8kfPVjTwCPWQRSGXqJANFI"
    b"isgPeFFg95nWpNApCc/inDHpCeHKDNobMk8GfsJjJoo0zRIBPeAFcRincZEzHsDQj8vQi8xS/0CEEeeeL3LhS9fPRBBzCVoF1Lk8"
    b"dnnoSmAEC6EGkF8RRdCqNMqYyFIJXPUS01V+kHsu54EIPTdPspTFHMsBcwqeRblIk8iNEhB5P+ZxVACjsizCPcc5MMP3DFHArjgM"
    b"WRxHIBdpIAs3zoAe+PFCnwWpCFzG0xg6X/oRXn+Z+zzPQSxyCWqUajR56LupG+ceRGxFFCWgc2HhcoEbmV3XL0TBmAt4vQCUwZde"
    b"JvOiCIuAyYClSWHkDz7zwuO+DAMeJIUAwnMQak+AVrFEZtAgwJD4AvoHNAwaAkyOXBYCCRETvtGpIgHEXoR9nsSJK6BLozgHUwOm"
    b"JAV8fpLLNMyKJAdx80OZZMDptAiF70dBGmo0kfSkV4AScBmxOM2Bi6nPPZCZAsh38XayJONZ4ed+AHoLypB7SZr6GYs94LVhMcvC"
    b"KPLdENSDhXkCvRiEYA4SVoQuiDDnUSSEiJMoTLPMD9CYpJknQQpBGMEqGikGgooEFDkII9Dh0A3S1C3ALkSiAFHIQb+jBGj1hMcC"
    b"F5RYsExkrisCGXk8KVWcp5Iz6C+8wieOcjCBIHZewn0/CWI3c9MUrZkMRQJSUYgoAHZ5YJXAP8VZaJQhd1Mm3CAA+wxVcgE2xBMg"
    b"1KBZrptHcQDc9MCCMTBrQHziZ0UgBIPmg6WM8riU4gJ46aV5KmQMEhtytPdREkGXJjz0wPiAfqdZkco4A5MFniLOIy/2QlAcIQ1R"
    b"MsjAgoMB9F0G7PBBSosI9CVMgiwHI4OiA7aokFke+Awo8cARpUESC7AkLAw0mgAE0/NyMAdgJUFGeSK9NIY+EimoXgZUyKQA+xeB"
    b"xYY/oGiFmzMwTiEYxIwbuQnhcwJ2ESqA/vQk40yEzI/SxI1AlMLAg4oTP0zxFj4WuqCPeJFekUbQtV7ANBoQpCLNwXpA6dAPIh8c"
    b"JbQ9lSEoKmcJ6DQXsev7Kc+BtigE+wnUJh70Si7Nxp5B5kYxiHwCPEsT0AYwPAE0BFS58DNoD1ix0PUYz0OZZkGEuiFclqIXYpJH"
    b"psNBFkF3UmhNIUCGfFBLKQs0HAX0h8yRCXEYyQTsW+B6PoN+AtPnMxBaGK9HRhmAf5yjk+EJahPwJMxdcB6gQCA/TAqvCBMJShgL"
    b"iAcE9BxoDBiJPJBgyrJKbmLwgyC/PORg60PugRkX4PySIvPAP0KPgEaAZicMnBjorgtixSNw0SAcojC8CcHLAhc5CC9oEnQl2E6W"
    b"ZEWepMBanjI3ZuAKM7wRURZgf3wvcjMwfHEaiMCIH7A+AQ0Gr+2BEwSXmoNXy1M3BzWLIjBdLAB7FmRgYgqQPQnsC8A9eAU4d3BE"
    b"Rm6YEBAMgUQFYSEkdFsQumDpQvQYGRjCJEqCAqwH2HuIGcAhByDBaDLCGC296XAX3GOeMi8Kchn5gi6PCbysYBAt+EUCPhAeQ7gR"
    b"+Cm47yAKoUlAFUQMCQ9ijwLLh3cef3j80Z2Lf3elTFaJN9SAAhQx3VDjBnEMtkldD1mgDiX0PHcZiKu6J9QHjYEAgj6D6XVB6NW9"
    b"opLFmS/oAkjwEGAFE32AyF0VXIg88dUtOGBHQShTqgPMkpulgUookbEs8RhdHuOBdRIZ4YVYL4T20XMvkIFIGbWvCHzwRWFZBwdH"
    b"DoykaywzMHlpnNGGDhDU0C98qg+iQglBDj2HOApkwaXLaoCVPoQKdIkN2GtfiJCurGEgrmHm5qYOELkwcdXNnBC9gaFXV9uAqQUL"
    b"zogOIAfcSijwMwdjlyWBpgmkPlN1BMLHuE+1A8ybcKF9ug50z6A46mYgSc6W+AAiDUIkCa8HplC6gvgQgseDPia6QUohYsgJLyoW"
    b"RCzUH+gJRJIIUwdEUSBPvq/ug4XYKU0ILs4FOJaM6kiBCdBVhAtdTwEGjniY++BXfXU1qJsAPyV9xrgSeW3qAG0C4674y/3UE1AN"
    b"lQErCqCqbul5EJwRf2TMwSFlmeoDkD0eE33g6RPwWgQvMrrkVJo6wJi5YF/oqiFwHeBJMiVL6CoKpniYgIiKjOrw0xhlQfGTgx2J"
    b"CdwFZQTXRiz0ikRAk/w9c1PEgbC3TvekbsRDtir1V3l+loqrZS2c1axvYa0Oh6jcbBecaoD0TjNiNIaD/Zkt1OhUb6ooM2Gcketi"
    b"OHjA5SucRsPlydHZ2S7e5eQVZfIMk7XiLeW0+NRRfmSV5uV7sfeW01sMW/kt7DQWH/NlR44JQl0+p9ackZjCTnbRylDRrOht5aBQ"
    b"rWjnoBg8kG0+sFA5J2iV2Wx2qoSXzgpbR5tG72puiv7EFO84KwVmk3ib+ShMMoq/WCaK3lQUqrNbnb5uCgq7zOwvmHCiaVaoNFQ4"
    b"au43NSeL0DyWG5fLIypmy1j5wBwyqg6xWCa1dRONvnsbr6ODqD5IeesavZ5buc2VpPZFeh23neMkobqQGs2JmX4sb2ojISABqIKu"
    b"ve5L97i6dM/KWLQLXpKckaTr83wVP+hL5at7+RZD+FngFORC7d0eqZvvNBWqDQtsA+UwOuvWu7Pvuxu49g+LXZN2YFLdgF2d1MKb"
    b"relgDmOclMUAg4D0Xpms9Vkh2MQTmfaJmmyyq4p3XJBNV9VZ26+rRGdWrSDzzLRCX0rn7nVehsx4rd4xU9CTxiEweCGtN9JKFcZU"
    b"CqTl/hChNmgX/rXaE+7R5UuEHW8NtkwQrxWGAIeJeml8VBWn+3/tm+NqnBoStedNKyPcH07XF8+5Lco1voxZL+9wyXysnARIahAn"
    b"MYxy1cXvEIBCWKtSw0GAWsQq1oZxTwGD0aK9ehvBUN2VEYb0wnU9VwYUlsKACwbYHo8E3ubn4WiZ+5q5WH2HznE1g18pnmmmvkDz"
    b"xmxBYreLx6aB+ShadCsVfAU14/QZWq7VLDOJLhFN572VCiMeWLOWx2JaBC0NxqTJ36l7rMSFIPVNiK2LEDVqCEro9kP9Ve7pq/70"
    b"d7anb0eswOt3JGppseDNZYmdb1jfG+v6RHMN4nHtHsTl0tDjiz26ElEX91STaxzw2i3je+XViF1v1B2JnW86Lkus3tvM8vfKqxMt"
    b"gM82AKwCwV7zPsWhvlCxSdFsn67KNAUjqxvwlCG927SNBh6no6fb9cd0Gg+LWM9MP0Cg27g+saa2Bi5UYNikJlzf9fWnXMeq7n5/"
    b"yJHb9JtMqxZRytyKugGfRp0LWpUBfnsXzeM+gdLTmfvmTQa9yb514zxCqhNO3K3lWs7JiamABMtA4JECfxfOTr74uKcacenDH0Jd"
    b"2d1VFgDMAp793FUWAp/hN/WR6W9cgeE31dQPP3b5ymOEBDBEaOrROpOBYaooGJaQiviqLCejg4nlGdtrmEUbCbORCAsJorewBKcg"
    b"ETYOLFchYWsjqZMjTkOiePI/H3mMppmUeVVtUIwgxmneP/qRnUsfRTBGrwRhVD0B8J4Ce+RDj3xUORtcwMjygKsbhn0RZmpSIuKx"
    b"VwSCPodREcYsjfTlrTSKH5MzGMNYbb+wTz83gkjrLAMAbuHQcLyYfDqvsnqhk6kDJbOVGr7jquJuo9xDmMd4e9h4SpEmvdqr44KR"
    b"GcoifUa5bKBrQNNlwQacRLAXXvtMeo3cPBVwEu/bI36lPuQGSZPHlSabI2p0iO9mqawxWOuEYDHDO4J/enI41KjVYcyqXL46jKfN"
    b"4/6AzIwcymsb1U6coynNJoT10ZbVJBTGxlArRtolRqcTPDlf31qCTYQgYoM8vmnMbrwERbe+UdjXfMJbT8Rec9vKBCUGM4q77Y0q"
    b"6swm9Q3ub9DEQfCOg7xrpXjtJnv2wMT+SUynIli613qf2u+z9vvMfh+33+NYYVkftqpGQjDI61t5anxQbgLlwH4OvOedpNQLe1Q4"
    b"aRdmaxT2qXDaLuyuUThQ0XKrcNQqS0zTc2O7uyW0cZNP7il4ks4nbYXZa3lDPtKW6m9wO9okPciXN2ZZZbsO4uV8stID6tb1DLu7"
    b"OgPAW69ZnlFxsR8vQShvLTpua1VOGd6B896t1VmroN2KkWWV4yzTFhkxKcOw3avYDaVuYW7rl9W+ayqzB32ptwA3+NdbsfhLNoI+"
    b"l8YentrNWRwlVlP+Us2wVL56utcIZ3dVln/Vg3PCDbB767ZII8Z71vczi95Jnd4bk2LZTXFp2Swx7Ku8FlBWtdMExB5dLUD2KNmt"
    b"3GZXQxqSYF9t/26w5K12EjLudFnBI/IL3WJQ4fmywzxQm0trtUtgGLnvjXrNAaFP9mfpTY1bL0V0LoCYZpfdVTNXdXtZqptSNPWs"
    b"pMMd9Xcw5kups6ss3BAN6x0JV/stOWVwyKzNf6tg2c5RC2oc54vxAdDYV/OpZJKhHnVwphvcBtV92lKLstdMkgTVbbWMP5PjUzrw"
    b"cD+G8DdfdQ8QOzpEsK4QC0kL64/TtJzp69GDsEMPsA16+61yzE9SXlz1UWfqV1OEtDnRbcctUO9nMbgaEiqIrohpOCYBNUJnzijf"
    b"hY60aRSCL2qISq4oQ4Y460FABSAoQ1E1ZUbaY53xU8lY8uPJ7KhMMjw0ySu6p0Fx0atl2NIbR9Mqzl5BoHJbTXhtOLdNnG01e3ti"
    b"VilM5aMGiVWblFQptadq6pCKIrO2VKIrYUyeGz1oUOCj2oKDLVvUe+9Uum46xqu/ZQGrhkNaJlogB/EC8Q8ZykkyWfaF4E25xJWO"
    b"7c5TKvCmlGaco7G+vtcZPk0Vqpl7NVM1vFkKriWipewmZl7SMg3IjU2cXbLXXfRKNlqt1bK1G1ntX6a5v6G7YgkStKKZyVBr18iQ"
    b"XuEprd/2uTM8H/KZ3Jq7R/M86guzv3D7i9izu/OoVrrmcAxCGKDg5KCmrqeqUb0o6y3ablijKO8t2iajUVT0FtVvnCPTV2p9ZlaU"
    b"aVj6LvpaN384odXJno49K7uLundHrfqoG+Ka6bZu3Zj13q1jbyegw17l5oH6dTr1ZOlllhObzFErxzntvWhcsqPEjQmTHam5fFit"
    b"G27oeb8yGUqVm7CeMQjo60skrk/eqhLT2ZQyPOsFT2jyIi7ycbXw2bspP2xNnDC8WaBcDt2a49V+h8PBBV0VRWk0JXLaPWDmHNa0"
    b"mCG3um4PZa3rhnnjtuqN6sxyxx2ZcqNij53TfdC8uBDYTfxp3flZSzvddZcsNqgjD7R90yQ2skwI3XURObeaWc+KzHjrikVvw/C3"
    b"+45vvMC7SbRJ/l4emG5ebY2MfvjDH/rwYz1NFPxtIJVdSPdGVmrhdqcjyzFNLHO3XIGZYk3m3+aNqWVrzKHyjcah8lF/h1mSV7vx"
    b"Ut9MqtjfbrMG7BNWc8Ckeb+t1xJZ+3RM94WdskuuSUzXk2d/o7Yjq+9+2halirdVDzQT9XZeQ+uuXOnuuIISJjfundWbL/ovmS23"
    b"5dhX2qPKFKQ31s2qcqOVXrcDpVfdxN1tQVirO1jrEnL7Sf+100FP6zH7mU6327q2tTov1H9TK2bg7b+Ide0svKyVfbeWW5fVcuu2"
    b"hJ3ONRufYQustSRXZW3rznJonYXasBDqRTBwJQs8H96YO9eZDzX5G1Ylo9MLGlErg0cLsF10S997Nuxc48NIuFbcigirx2pgNWw8"
    b"uaZSIw6fptVzUZt7pTyDNG3+VnIdgio00hzavVAeXtcc2HVXaUwJUFUE0e686h21p5tjjTGAAdkdWpKBuzZ8TR8IeP0Nl/rN3qiR"
    b"kQ5zJeIKZu06QktY1FJpGYt1pFG0csqo89d9mJi/LbiFy1zfkYNTqYsd8cNDXhhDXl6NQzs26+FYn9AozLa8qCcmdEZku5MqYWbf"
    b"LjTFbI3ttKQBZb9YzO/uj7DsKFy23TsDa9lZzW1vOuX2saezFumk27UQW8MNj+1JSBpCf+pohmf+MRsa9CtGoBcGm+Otv3r6oQeH"
    b"o8YmxPQG3vl6iAweDgd/pS7/pZvth4MH1bdAfRuqb6H6NlLfosGoMZJVTYDf5fXBuorWQBRgOjMRIVGkLxDrKiYBHSoFErhTbKm+"
    b"/lonP9I8w9wu6Y0y0l9z7FK/4/CdD1tOG5NQ0mA03pNj3O3pcuFGHEKBT7VfT46rUUr327qq1LZb0hFdAMIROigbzmNy1VimWNXK"
    b"p4GqoRlmcml0MW46uzU+qK2DU5Iq9Rin0nHg0Xs7HCYosW38RKcJ0MXP6wLVanE+v052jI6UaxVovG1ciYwyr76O7B3UNJJs6pRC"
    b"UEtK0BAhxQTcVTpy/qq1OovpJiZT625oHEuroV95xTKhKQHsVCJ2IkdqNY4+7aSL1bEA86rMuFgbo1eNNH2nkxsamrAfaw0vMw/W"
    b"0p8i+065OF1lcunGU8/m2FacruvLG7bAzv5xrkpA8NjRFAe1OvXA3W/+8O5/fP3eiz+4+9w/qVRi6nanAWUZaOYtWztp2YajIM2E"
    b"hxZ3IIWkvm3CSX2wDnMwY6AS4g56059NiqoQXR1+7A1a6zB9SddM00frZx8rk9B+Zr2sWqflQuxN02Un4rKSUlX5x3RKsHrysbj7"
    b"ipSeZGjtnGdl2i12ZlK0dp7D0zKf2fct9bw4NbfYWqkbm2kha7eQ1DKR1a5/MhnJ/EHftVCU7HGdbGVNtjWylnHMWgZjnFrbVe0e"
    b"d9dJ+NasoCfLmYV+vWxnh8dV6qx2LX250M7V83K93Zxolhq95dxo1nVWdpK0c/VcZD0Z05pQtexpovm6N1nauXaKsrVTnPVlNDvX"
    b"SlR2RnazvmRmdaDOxGYVjH0p1Nq5zerX2lD2KTuVcIWxluHLziV6RuKuhqPcsN+vNmmuJDkqbDmqOd9TMX7so1c3a7dRrTZXi008"
    b"1rB5K09ack7eGIjc1HGRii/6cpzVCvZnFavfOdWXn2xwGC8WeOfXZgPIw3Ph9UYep5tJBn4PXHETWmwFW3wrnQ6aqaTtzMjpbHZz"
    b"ktfTMdc6FuMbAqF91MaV6WJ7erCcHc7U6ckyBMDzah9/5PKVD2NqOSuJWNX2NTOmOWj4MHNaWfLtZlCj/OKHKAxD0+LR1jRf7s9S"
    b"5e5Hf+HUfbXwBUeKA0qpi2VUbl0dmlqd8Z4yKytz4eM2Y87JPz1/97uvwe97f/jne1/9zcl3X3vz9W/bWXbvf/4PENb9+Zl/vPeV"
    b"109+8h/3/u21O3/4lz8/87k3nvknvNXzlRdPXvndnVd/ev+Pv1PMf/P15636Tr72ubtf/w2U/tgO/CJmnLz8/MkXfnnn1WfuP/uf"
    b"AHzy4ivw+eTl79//z1+e/Pblk9c/d/LdX+oLQn8KAN+2sDmOaplz9e+3kPaHlVANP7UwAXeh2IiBDK7CMxZxFvhyBA351Z3XfnHy"
    b"7Gs1dI6j87pTAlvKxk6fdOhMn+1stzUlfvP179Tb9tw/3/n9r+//129qFzIAiW/8+HsnP/3GyY++f+e1Lzom0buVMreZSJdSjzfa"
    b"ef9P37r377+HLnnjx/9896s/O/naT05+93/uvPrC/Zd/itenfuGlez/7vuIa9M3d7/765Nk/YPq457+kOPbG535y8rNvAhMAxiGK"
    b"zxO1JltvbXWvnZq5Ghrol8B9CnYPxiSDWruHNaehhmv1zQjYSfWNN/23E5sbbc8oYGcw7yxBwlB7UglG9XxUS4cPHqzLFZ3tjt5t"
    b"l7SWW2rCn+qLzvIXT/UwwqStrCSgNkyvD6VqFqg+0rWMkO/c+8Xv7/70hfvP/urer39959Uv3f3G7zCP93d/cOdPL5/89IXSFN15"
    b"7UUwBnd+95U7r3755E9feONHvz/54gsnr/4cLMedV3/Vyj1dVXX3f3/r3sv/DuYNINEtOPc///wb3/sh/HZ23nfRgSrv/+FlqObe"
    b"a69o0+Lq9NKgiVCBHtY7LPrbiw7mrqaUjB31/Mcv7/6vr4GS3v1XMGe/+vMzz7/xzV/e/cV3oNV/fuaF+8+Yi4wBww9/9Mavnv+/"
    b"z7wI/5888/rdF34MA2cH8+z932d+DjYyTlI0ti9++/6zZGxf/d9vgAV+8Y/3f/S8bVpVtYjvpZ/cATZ9+ct3Xnvt7ld+DsYTagZz"
    b"A3yECuvmRtmYN19/TtkLZRTefP1LaIaRmV8++c2/n3zn+6WNbxL5pWfu/P5nQOQbzz6PluWln5y8+uq9l79Zjv+ByXd//SNoFF3e"
    b"/Ny9137usPBgoWq4+80fYwr2H3//5Ms/VK4CmNkm6c6rzwKae//vt+597ncn//Krk5/+28nrz5z84iuKb3df/D+YRBws3jOv3/nd"
    b"D9A5ffVn9773zL0XfwntVa04+em/3//PnwEpbzzzzMnz34AnZe82aVrOb7e3/Ji7tZbm1pdK4nXy/XKaiAxO61KYLmQ0l1Le2nXG"
    b"dTQmoOi5k6Y57VHp6G41I7VXvyls2DnpfUrrrDtTyoil4sxGhxFq1TBq7NhHo+hcoT9QqM14DFRtk3JGaNlFvhVd1m76MBFmy8qr"
    b"+cEy5mzPEeIU7XaPSdyoY6ndw9TIl6o7tL6JTzG69swwvQGoOqC+V7oeWTc9WU20e/P8djEThaFrTvFCg/h6uzEncNu9V9mBm+1r"
    b"ioMTL/BZ1WadJtgO7DE4fPVV54HFtqOTH0OJrfGYzgaOx/AJ55nGYzzdk9r7b3HesoMr8a2xjs9Py1fcL7j/H3dv2t3Ula0Lf+dX"
    b"7FJeKCnIsiT3LkwGAafCqYRwgJxbdV1+NWRJthWrK0k2pihqmBCDDRiThN4QAqGrEDDpaGyaMe5POfGW5E/1F+5s1tp7rd3IgtQ5"
    b"945LVSxp79U3c80515zPVArQwY2dcokD4lie5x9kCmPV8QHlCZ7w+Bv44fXLs+vnX5krd7zQkFXxxbEqPCCSvVPIc12LusVNcrJQ"
    b"zfMQW+LIIcA9aHichYnHDNXsXBc6MHVC4B60AuGs5dEwnAnW+b8VopkCqL0JTjPe0VjxRCi3BD/udxnD250QkWy9wZpVYGSO++my"
    b"qi1nkhMbF48uCSFCcOYW4jdnKoLuabEdEsLBuynuqXIgM/83wz7bZbomTa3OXnxaba8DHu3iSlpDk1Zo1X/g8NJydZHV1tf2v+3/"
    b"aI+B1zvn5xDdCcQJLOn/MHC1cqGEyzFBQCJ8tUR//eLfwJd+NWoPa0zsgijCxyE4PrIppXiV3YA+Uw00uejxhusAR0FfC0rjKfkQ"
    b"JBXIFFw8zKFdjl6n5zIRKbzGVeuLR+utiBTyl7NPktHirC30TJ0azmT3T5A4tmpVumg/9+yf/dqri4K224lUwu6DXe9H0t3Xes4l"
    b"ZHs3iHrVmbKrbK26VqsS6YjWbNqU+PePd3yw+8CfEhKbIEhRa3D2MFKN3AIolwj3LljausFEPllNjdOBGKlkkuXUeLAc+HN6KxTB"
    b"Qbw8Ik5hcZQtMlYuTpZAkqH1TgUJVx1p4J7MZauHnHVbBjDCGUmtSMYC9G1bMB7rjv4t1tkJf6Crf+uJR//W1dP9ty54AH3+W0d3"
    b"FC1bsEit0WqDY84G86jprQZBzj1sangx8+xpKzGGDHtxvLF83Jy7j4LriZXaxceNV+eEgPz0BylMohbu2AtUYr48Zc5eNVfOG7/F"
    b"yn+LMcjO3jHnLoPgXLs6X7v6be3rE6gpeDpbu/wIODuU0a/dqC89XMOUc+YzFG5ZWYFqDdzaqOVb+aK+9LRx53h96YKUl2tXZ+qr"
    b"c+bit+b8P+C7efYMyt7XbqAkv/y8ceInc+7E2urq2ovzVmUi/taVz1CfcGmZq6Esc6xtgIe1H25AQxt3jzde3MOUn35DCdRAW//3"
    b"THDACqgob8rQIwHtj1qJJLe2KoaMjRY4KBnPBqo3Fs8i5y7HDof10Yv1E4s8C2tPT9aePjXPfla/u4BK8Ic/m5+/YNWrHCb3CYkN"
    b"a0ImRL58hugOJta4iIxKfBwl40uvkkVZgvXVOEtbaLBrUm4cFY7d6z3fK3smcl1eblRU1SE8KEWNZxDJzvtls3diA3u/HINFyeYI"
    b"zfI2SVFSH+MQNxs9+71Hb+yXzd45eqPM7zjfknlQN+1kHLcOBseSwxeb9CUosFMzuUyqatN66wATcaEPJkHwsxBQmdIqIaFp0+kW"
    b"N8O2eSQ6TtFBqBDiMLWFggZTlVbRXCxWPeRf9nD/po3lFucIYKDW/g1L1j1BLdNXAZfKHfBgkLDwCFAzdLm0+8sUQO+pQ2WoxZFV"
    b"e+XY8k0FPulCPqwWkCwc0jUFgnF0S4QqV+nqWyCfzBZQReSOgGUE0HJxsrTx20TM6z1aKaA/ddnrZaWUTGcSSa9XMmA0cZj6e3tw"
    b"fYYoqM9GWDFrDIWGHUGF9cVghf/UVoM7+KcYfzGihx0cv8Wic+sNZjOPOGVrv8PjX7DkPM0mnY3eUFCSwsWR122bTr0IYqj19rlG"
    b"KCiGSGz60L+0NfrmZLcGDEGP12IV4fAqKJs1MDIQ2cFKv0JcHGTGPqTfMtiektlOm3e7+Lh+7p6RTU/vMZjFxHsOujnHOUJW9dW1"
    b"xvLR2vIisDDmzOX1mXlg8xo373M0W+DxkIU9vqDzkvM6dDIMn3M7EFY0LoFMYTKfKeP9n91lVUyzTj+2gXRyZKSD0wfXsSgxQTAA"
    b"PdycJpBqbFBIvw2wquBw1DyqbvwQO+Gw4KRUvknP5K+Z0NhCYout2bBUFKRJJ2to66zko5ETSJyvISsl+ncPEb1QjxGHyIfrGt/8"
    b"ZsCuwsY6VYYBslIV/T7D5D1EQnq3koVdoyZXouyvOXtv/dg9VRLCi9nT8/Wvj9bPnGhfe/Fl/e7y+uUFc2URGeXFC42f7gGvjHLJ"
    b"7RcgRlhyhn0PevNR49XZ2qNzyGRr4su8jWRSThYmggT5Jv2oNUaGxkh4mVs6CIERgAsVZwXXmc25iResENYeJ+znUfWK6K8epeBT"
    b"ZxHpyTJdhCXyFVcp0tFFtIptvDA+11aqYJNr++ST00ELV2mAhkHXiTWbOmbgRpO5HLkRJEtZxpn3lXpbVCRLZQaBketsAZ97NA5q"
    b"vc4bASUZMgj+b5vnZTWM89bAsxdBJMBhZkpDTlAmfxbOOuy9hpGImfMYEtykn6bMwc3pAp+HPC17hI8i5PJcOZitjgcDhwPNtMTs"
    b"rZTWdcS2TO2pHvYr4fARnabQc29NmscgifTaqqV+QlnkYIiNMhD42CXKMyvH3B5ehYtlS2cluleih6EKiGNDKxCuMXr1O0bRArDf"
    b"ZsSjHG7hIDoVovPI9I5e+STe30nPRgJ/no7G4L9ooJVjglpKQeXNWz9JZTmzBtnSONrUisspqKLT6Ldb02YEle+djK8/rJ5USgGv"
    b"2ZLl47ULJzR1OjBQuDeqFe/weRy2KZ3uTMUz3SO9HbHueLQvmumKj3SkepLdPR0dI8lO+9KRIoN1dsdHeuN9yZGu3mSsr3ukoy89"
    b"0tUT6+npiqtJRzv7RpKjPaPR3kxvuhsj+mGEuI6eVCzZ15WMj6qlYlC7rhiGwMqMxvs6+3o64iPd8WRHbxLEgi7h6RKy40Yoji2V"
    b"ccgZD8ol4giGYcVOcCTnUrbaw+PIp+IrEfBHaiQlF6mIH0EumzI6g/C6DKtzZy1EqzDFRRL6BXQWSrfBf1RoYcgVM7YNWOm2UVAG"
    b"lA2UJ+R9KbM7OF61A3YV/W0iu+aKab2XsBawFaIBywtSGJ+GjQyut8pAQLgSWippOfYt38koYFYyMAqTQUXrLgsN2LFfHSRb0iHH"
    b"zve/G/GRuZSRK0i2Tr/w8dEycGp/YVyeJl7jw3l/xYEiuQsgoTQJ6KtAqCycGUGpEzBhwm/KGplkFc6xkuIHGG92srwFxG0BBJD6"
    b"yqv6vVNoXXr1Eaz4CpoPAls3kcmU2oD9ncqwpVf96tHamXmURb67UbvwyFxdabz6qnbmNmy0Ax/sN2qLN2rzp9CG6/nM+rkZfbTI"
    b"/nQsIQoPcixm1zi4TFRUM5XDnqZOilEmrrH28Wo+p5tf4pOt0/nc7/4yEI30hd9uf5u+9Qa8Y5cHdiZT45k2NIIoF3PsItWWwmce"
    b"Gdwx4C3TmF4/lQWNR4QIfgLmTLjQBJ0JMiK2OR4y9g80hPVwD5RCUIRoAiZK7Pvo4wOD+xK7dhzYEbAkq4hOp/TTR3cAxHV0iNjh"
    b"Amy/LJKmMTWqirpuqdhNfhZhdFdddvAkygqGv5tcCF68jn1wer3M++TYRyo5WLfBaKTDrW/Y2FZNs1fzGhYcBWM0g9cVo8lsDrkW"
    b"tlmSHZJkE4mPsmNxFRLQitzIfC3gvFF5p/8giMjFg3+OhN5Rp/DPlbcH4D+galiQdmOQd9FMweU5TMXoFbGQaAGwi6h/GcGOkgcT"
    b"4izAsofyEdSghPqHQ9KQQwxb0OYvwwYaB9HXkFf14jITJtHCN0N0gmnFZGcKCfG0drvgFZndIwXrWYQpx7QA90gL00A7XlNayHWZ"
    b"chZOeDQjt133y7Lm5m+BtCMmt/5OFuz5MqAyM3jZsEGzqlk9VpFSvkjBNxb+Tfd9734RqF39lm+01FZSvA68ixf1ZkrZCjpvpwpV"
    b"FnqnfZ6z93mJTB8IAEFveKo4lSlrJbhfBOTlFxJb72LolVcxyouAbl2i+JhNFdPsXwsrJKw/Fr6r+OF4A12CF/DX8bycySfLE+hL"
    b"FwyYs/c2V9aXjuPWpxGkhctjKYQfR25hghjo595KfyveKnBY6dtFsj/i4aZNbwEx9PhnmHPHzQffwBm8fufC+o2fa9demdcuwukN"
    b"xzme0+eemSfvwfntnXtT4v3fYzCkxIc79loeEQGQ/KiP5Uwy15YuJ/NJoDuTgfqxB7UvHtSvPzDn70pRPTA+mU8WmqS+en1tZUXN"
    b"kCrmaXiD/M2Vo/b8vpo8maW0yawr4Y7dIt0R6sX+wR1A1hI7d+x8f5AlXfF03873Ezv27oZn+3cfGERT4HYQaduZ5rYzz9UeUMug"
    b"QAllNBrNl4DEB6HG7777M5Df4FC0rW/4cCzcceRvQ3ibv3J67em8ubSEjgyzD9aeHjNn7689u2YuHOVUIcw1BPOzfuzeMCzSt4za"
    b"1yfWb16qr35pPnoJvFLjm6e184/MBxfXnl03X3wJKc3FJ2jJf+fTX2ZO/+fMHfh/be7z+urc2soZc/HzxsuXayvHe36ZWRDW95TZ"
    b"nF9ga4X6T3cbT67zQ/RQOvrKnF2onTxpPvtpbfWFEevrjRpWNWLyd3/g0WE4iIag7f/ryZ//3PafM+cS/3x+pT/yy8zR4a2hd4Lv"
    b"bPsNDUTozcbj/6OBgO6Ziwvm2c9rp17VFhbjaFXxxen1iyuNq1fr/3gFedeXHptP79SvzZj/OA7/R9eyn5/U76yi5wW5TWEW6knj"
    b"p5/Mq/fWnq7y6Nau3ofRhdaaZ8+sX7uJflXHv4Bk5vwyJ0ATD3Ri+7Z+9ZR8tUAaTVECZIcZgxGM/T1urL1YWL/0qnZqfu35Mg9t"
    b"be6CuXCyHWhA4+4XtVPfQQFyzJeazsjc+qUfaBagcfFovBMVozgLH+7YvafVqRh+O4SPoLDgsLYo42K5haDU4b95zBIksCYAa925"
    b"B+qaDMA4N5+7gER8AA4+VQgWJB6Jyl8UhFNFIbSRcbUATQZKX7D5GBKBo27pj1o5VBhWEqKHowvSIoDNRBQokQHVLlEtVyzqXzzD"
    b"qaAW3yooqJfEpWy2VFuTjiNHdMcep8JkPmgBt0i0FO3IGzWqkWwlnR3LVoNuJop8iO2UyAlz21wpY1G7PEWryKlDHsnt3kXoOiZY"
    b"HcJIDlKJRxo8UkZUCb9UDpNEn5W1iaGC94pEkQwbiTCBxVcjJWgLqa9lW7yHXzQiyX7SrsaNMAYQNWjEpzVe5fGBXHXlUOYIjgA0"
    b"Py8Ug8gEiKFCllw7CyR3TtycPoFu1ltOfd4ybwpZS0Aht03KrOp7ylpLjgKVOguYLQpLnHZRX58Kwg1UTid95vHLtR/PW5TTTTbR"
    b"bgyd9maAAIoLMnmc4N0QvcK8tz6rnz0uL3bQeiBsVCZHpJyPKLjM3PLYWq7NkyOKIZMca5X8yaHBIjXVTD6vi2uS4uTtscahtH7G"
    b"nTc2LQ6ZBHZSFspIEh2AqodkbyxrMwRwMBo37tVvraD/3LF7wJKgBoTGtnZp2Tre5bDP8VCjKRqNLZyCMKR7IEM75OZjXTE3k80F"
    b"Ma/pmiRypCxs5/BbDbamcO3pt7wyaqeO1+bO0k2yWAdhw1otxGQscVNF8ouPrbesimaTSavFHKxWbViE1Y62/q4iMNAmA7AOiaPr"
    b"1yyyWa8eGYWNHKyoYGZi0rIC2lso2WOeFxiome/PDsvKw/SA8Nf7h7UW2emxJepZRzYxXtP+C154itHaKnm2Kwp7scDzDdNszt+u"
    b"nZnnNCqHAcMKDMI6Ojfe8zBApZqAQWk8vIW8zt0F88XN+snHeEHrvW6Aoaid/wlmVd3Lwu5TLkLkPz79BpYl+rEe/dJceGTO3l57"
    b"8SWUCmwmMpVULS5gsVxPi5V8Gr33bRpCbBWt1KOe7JPR+fcY8E2wxB5chN6g/+zXT2qXH67PXAGOzioHK5q/K41t155fady8D2yW"
    b"eWbVvHWlduYm4g+8sLxyW11hzWgRrhhVd4KpoAz8GuyUSneiPMSQxEMenIZlCOq5I2lNolGEm9jjK9/y8gVPWjg5ArsEtgi1SXST"
    b"tk3//3pC3CDw0TPKgVRARgET03lpq5YmA8QEipKG2uL9wxqAhDV1jRPfmk++Nx99v7Z6m1cNyyq4dk4s1M9dV7hXQ7LhKImwBYA4"
    b"VWj5+HVVWgEXlK1WKhdHMomJgxWCxwsbMIP6lqs/XzFvfQ/Fo3H1mZu1n0+Zsz+un3vYWEbzXJtxh+Ul9xq3onHnKBA988x1XIKn"
    b"npMlw7e1s1fN6yvm2QX4gqYPc48UEpaX565z/9ujrJxhLZ18yorxPev6XW7Z5Bb/5Ac0rPjuO2OPQSLJnDZVT+/IrT2PFGjxDh/c"
    b"69e+tvpX/+kmTCeIIjg2J1Zq127zbJmvZs3jCzCWGxgZyicwLFsFn0uMMtJufDI5YvHZ/melWpBA7eOitKsq+YoE7s0VmElUr1hi"
    b"x7B2JFcypMJRa9mINIy4eTu5wXBzbry/RnB7QVJ161jkVW6UK0zz5cG/gAI3TQauPfqCouHjH41OQSJxt8F8zN9mARGps7LVhLDb"
    b"WF5ee35LMlzUm7iTqXyNzii36CPAKW3HgHzEYsfJQEntohy5kbh69z6CN++d/Rts8hFlyogtS2ThTE+L+argUV+x9H3EjbNDkUML"
    b"XElrSl/Vf09NlRWp7Fbh9Uklq+kNZTP0gRjzZCJwjY5pbAJzCDTqH+xHMWccwfOyhbFIrphK5oIaGyZvu2z2a3mRL9v44o2toyzf"
    b"bQOPwOVrMGH21RvshrG/Zkvi+o2u2Ph+TSFYFTJThD4mq9Be0TZEwM5UYDHgYNn8NyR1+TlyfsuDfL9stpogUi1P4gUHwdwTqpH2"
    b"1gEm0gxaxQWrsi8zmikTjpmloAv4Iq9scMkXdiGzNL/1EyW3faAhArbt3BP+6zhn9ckwKG7kMANOEOIqYAgo9ZbwiIKvw5MS4aGG"
    b"v5ryAH7aq4YulxIV2CYIXWVdJ9qLyFw4X/vuhsDaODXfWL5TOzbLpqBANxrL5wX0B+FlMGNpHD6i+vpoF0OeV7PWTDBW3jvWPckA"
    b"wyhI0GNoo4Q9niTQftle8antsbLqvY5kJh6Nem47xUzpE45OPVkVZhdBvmy0yy0R+vgn1OrJAFpHZcq7FP/wkHijgP5Zrxz04xON"
    b"yCiNkJYUoigejF1UoOaGvqHWC6/GNr1ltME/g7FQePbqSw/NF+cbN26bs3jESySdeA9MJSaGPJy8dvKkIeYE+XR0oCR7ZGNt9Yz5"
    b"8DSIAHzsrC8dR7793DOEb1k5bnTgUWNMxRIGwq7c+om4dRA/FmuXzhhZRLOCKtZeHDeUWx4ok1i62XtGb9SAEkFm4Tq4uVB6/dz3"
    b"Al9nKt7TQ6hj37008pO5atbCO6S28jJEVh53wq7d+wZ3Hvho358S73+0H0MJB8ar1VKlvx01811thWI5n8y1VfAoKOSyhcxIZPQv"
    b"BFSKatGAo4i9Ow68j0W0U4p2BkVsd7ehfSrW7sz78Q5cPdbFRKQ0XswUstMRpOntPR19HXEj+EG2MDn9O+Pj3xk7GIvSiHX+zqD4"
    b"J78z4l3Rvvf27om+u/N3Bm+uwLuT2Vy6/eN/j+2IxDuj8WhXJNoXj8ViXd2/q1bbihPtHZFYPBLriMSjocCmkKNFeJbbbdqSTA0g"
    b"6OsWgfQ6YMG8bknCXkQIrC0SzXXAgnLdouKEDlA3RNu2qMCtAz2RjkhfpCO+xQHVOiBAN7cUK9ZXgmMdSMpyFADRAXsMtqjIqwN/"
    b"3L3jow93b5FgqwN/Hd/C8KoDHZ1bbEDVgVinLNUTSZU7sMXGTh1Ax6S3Y33x6JY0FNbZG93igY+q91sCow5YqKhb3FCoA4SDusUC"
    b"PxU1u+BOB6KyWB+c04HYFh3ZFB54YpnaJaHtkBwQr7WztZzJAYOUacMohO5ls3PX7l24CaKjsUw83ZFq6xzpSrZ19/X0tvX29HW3"
    b"JbtGOlMd6XgmNhpVVRxk2oHbpOK0JCYXKiDxwguLoeaFWFCBptMxJg3qfD2Z/Gx1HbD0TUx3p+hqnw3IdCtdUSkksPXodIEOObIF"
    b"auQGKOKYJIKhHqeyaS02noyrZz1X2qvyd3Qo2rYJeBzaZu14lqiKN8M6RA3UchAlNefvAmFleorkVTmz6/9YAbLM58P6jZ9Bal2/"
    b"vFBfuVtbPFu/tQIiOErcJ5cYPEflBpUBqyjIJKTvUMeqJbuRUjJLHMLBYnkC2B25XfBxUJsKSuhiLdUiysUqblIYnkwyLwpSykgr"
    b"7Q5SHuX8VvEDlWqbZlERBF2rBmsTmh8oZSMuRGIo6iZrCPNN/BC2Y6tNFcVTqGKTHoMisEUi6FOCZlixjpwehwQWl0qLutzUwAMB"
    b"0Q1aqtVyWLGGYYMJPBTJaEEiRWOQHw1Y+Qg82IPnzk6gfMXCXuu5wzLOAxTVEajVAyBV8QbwhEp14PzrcyNa3lbdEPNXGMC64JPL"
    b"bUkhsjiZBkfapC8uZMAzZVtGER6AeABVqh76LwJ7dKI8OqE9teALaZzzLP5xIa2GXhN0zIPNc65SYtw0ZDZvfLI3ASaLdXlBgLJ+"
    b"qBkomG2o64LbEgKLpBouFYkANhO8MWG5AgkXEGEVhilGpLABgXFGG8yrIm/fYVUcKRarLsgghz23m+KpqD5QwAZexkp1FBtFGJtj"
    b"TuFeBU99oVqsLIyBxJol+czp2+fsjJUw5ISLsWv3tBXUu+VQFXHIyHRGxXLC47Ep6otHGWS3iAVtaLqIiZoW5cE1+dqbe6yu2sWv"
    b"Dbt6scRwaVWy6Y2WEHJ8QvBXWMCh4LR2gk4R+C4FNKYLO2mapyIpYYahYZfZpt0PBZzRoxNyZwAXBJLrAHuJ8t5ALSM2y8NXl925"
    b"efKoK6rEvqH9sUczBAQhN8aCIaRmoE1vyFOQt2xi0DocI8TxKFbSNhc9UizmNIM+fBB0aDatJYLbxDElFXvIxYBjDCbB/e//Q2LP"
    b"jg8HSYCW5gwVbk6EsTvtRqazlQk4t6vjQS/znbRYDNyVtJO582aQikD4oUCOJIU4omqjNrIDsq2sbZQKm7POZfO2mhh1Xovf1s9f"
    b"rp16Xl951Xiy3LhzFP0W8KYdYVrQNuHMXXPucf35l+aDS+gltfqY/VebYrdYamU/VjiVoVBpKAcFU8KsFvg3Nq0Vhhsc2ov2h5ws"
    b"zDZSzlazmYrfBkmJmod9DFc1VgwVbW5zZhcqtmYS7JlNa7g7I1vmeubUjXbdWdka17utmqGuklXqmsqIkkIU31GAR4ImxaSIV6v4"
    b"mTErUKWBanKsoqSln+47B/WlhEkkQjOkhuZRJ7vfGDpsr5B+o3CEVgf5bNNawjWoZra2dT8vsmmV3Lr3vlhLw9r429cm/S1epnik"
    b"cag+LetknX7gAS3pB259QTUU2qLuNHzSkpCJBmtGsYQOb5AFmH8MdyCZ5AHJ0SAdH3V4tqqcQ3DUfU44T3cvDW9rWlttHCrJqUwQ"
    b"ZUvyBPw14+EeDEIaQe1KEWMiW7VIBBJ2H88l8yPppDEx1Q//DcWGxVLF+54o2rpwLNABtE8KDfXH4gokp2uwD7Y42JbcGKTjl9oD"
    b"dY16hbxoifor9J5uO7QrDoIm4JuNK41XS/V7p5i4Gx3RaMX4z+NfGPVvjtaXLomn3eP87MXn9dWr6g2JcgCg3yCaUcIBLcVvi1Ua"
    b"z1b1y2EyJNd9BAl0qcqmkYrI3oZP0fV4G7bNOsQdXAGmiQ27Txp+zpobeQqrV0AhYcdnaf0xmsc9hohT1Pq6Nn8JbRyuzpsPj9VO"
    b"vRIod+q9wMXHtfmFxo3bKgsk7WzEYvVkbJTmT6WtiyMPLZjGPUw52If/M8ynbAzU5fb70uMfVtKiJT7phpRjeNj28nce0ajq4jZO"
    b"eZ/eLkbdowo6SXwrEf5DbHLETraU3ePU37AmPuJ9qxIcQPOqZKINB454Av+xY5aheV0ykW9dHuyDu0YvHsOnXs+krXsnOpuFnMmw"
    b"MGL1db6yhSA/b8ag5YoXVhAgQq/XBqsa38G0mJBhxm2tuGMWkGs1Jdd0zsrurzhAKJz0lhBfKAS1Rl/jndEw5A0Jn2XUkdevP5CU"
    b"P2rU737h8i/gNrRSARW9Sc+rCncSFyk4cTBMXrCVgThe9yfTeDc5QPYVtp3a/cvm8VlhdrV4gTGbhCRJlkpsgNZ4eEsolTmUEtl3"
    b"nEIcgw+L5YxRf7W6fuNn5ehqfv2CRLI0pkR/Fe1Ea9eQA0aIW61CAbsOtO1WMocRkIYn7gYqoXi8ZNGGt3w8XGPq/fjGPrh6FQiD"
    b"gzTZunfHsj9QKL8D+8UbGolOqmxVFNJEYeOZRuMYs1VHZIW07rQ46aTwVpGO55b/iEMXVHFeZlX8LrN88dOsSy3X6aJcbPGCpAsI"
    b"2UJbNnR2Rhwyst0hV8uReqCxB5mRRX3xDeRtn3oNI2oSC98JYm0vB+0CjvUfe/cNJj74aOcfNCusD4qpiWDIer/v4z17du/5Pe4d"
    b"YIHl0w93/BGedGj2pxliunBcKijr5bPVgQ6FIT17xlx8tH7zs/qxBxhXaPWyOXcFuCrgxtAMw77ZgySWTY55/DLTKIxhs3oNWbRL"
    b"q+aNrxqPjqHV94VnSAtI8WTO3jPPfuXWVVQ0ZkWVGIrpolRMqDIjZiA7L3puL6XhoX7qk4ZEg4VsLI+gMKPKNSwDbsDfi0woOdnA"
    b"X5OFoAOuSaxuvSGWkKJOsntRCXtaZZaRB98+YCiz7H0IKj11Xlk4Sts6YMQ2jiyUIr6xMmHplL3a6qH78RMVUpLNyY0GQj4HuefW"
    b"14SIStq3Lc5jubWCWb1ocf30S9ARj2ow5qnPstGSlXIUo3sq0G90gjBaRSWKdjjzOPRrekFv6A5bHSI1MagSKRSxjLRaQjok9DLw"
    b"SpBXyjV8xLMbQ9BJYhxLOdd7LCaB5STUgryHNjFtnRcJb4HAdSyoix1z04rBL79Bu1afKbTajSn9Gq7rMjD5r4rrxOBNBSjGY4O0"
    b"sJt9NmAbbkA3TapqNP8AfQtWk8B6VgeQzjCvNRAYH2uTlF0Z2GoknczkCZQPFSTKc/KfDLaovBAe+UZ99bP6yl2m9IrxXixm1BbP"
    b"rs9c/+fzeXa2t4z4pAuPYhQirZKN2vXbUCDigH6OjkTk7oDiOZTsMMaUWX6ZOSo82vFxOz2GZ1AdPeZMjkTIyctHlEGqF8yHX5Fv"
    b"xT04yDv/+XxJGN6RsaHbpg6NBp+ewUuNiTxMfXs1OWKsPbsOJx2ckFY32KeNw8yhA9rqZ+gjsngBvvBB2Tj7wrz6iNzQroi3R6+Q"
    b"ugbDBp76rn7/lKrsYWtF8/MXa08fYDy4pccyRqnQe7CLG8IfzEsz6+9uoGfEjZ8lZ45RUWXryGzy4c/mmVPm1XtGLNKFAgVw8dJc"
    b"8ff7Pvp4r3rTwiOv3rPYyQ4cQPu9HuNto7e7MxpV3nw4+CGDxYqD0WEY/19/N2P341ddznBzVVXwWK44kswZWldVLym7/14uwHoW"
    b"cdV7+IhTqaqOkoW9pmlUXYfzG+uVm+qWPUKFuK6RHBfX6RbFH73z2uBocZC8Bs85QUTX3bppr2F8Y+W01gJfDXWQVNSack9qqv3O"
    b"L4cCu/v/cv01Dyr2bExVY+PJQBSLaZWwxR8Ksota2Kj/8LL+cAbZp2F2s+V0tbkLjVcnaleviwwopLtlgzH1+FeDzfDvlDbfvFuZ"
    b"QUWfFmiln+UmZPW7FbWKRxCsAYcSfBTqqGJua4ZVB2wE9YJM2w2NUvrXoCk8LPHGKl2yeUIP4BcpYFrltN2oUsAVhtQUyuN+X8kZ"
    b"1XUSYqko+xhW84acNqOYRsQBUvAhKoniRFB0RJE0pe+4efYOnEWRfHLaaLz6qr76AGFhFs7Dezhh6w8vsgGp7i+Opdq7ExVEwUIR"
    b"a4+FdIZX1qso0B0rAotyTY/t+CM906nCAbocDVrKJ4Q6xjchUkCF3EfdJG2UsOHuPfswzC8ASwDnPXS5xzBv/YP90NEHlB1Ar3yK"
    b"m+r4LOr/YlHEQFr/4jq5NZ7Ci59XS+bs7carSxh/5zjeczAH4LmHpD2Xi3N3dbk4YeMxaHNHawd1INYDkELjyj487CXWkFl5porX"
    b"xGQUUpzQyeGvE2VoRoU8I4MtOqiBHIjihB6Xa0hSiGEylkttUkUG9WzRVvmEa5ZBuqDrACkjhg2ac6lbxG+ZkiC3dvweH14NQ9nb"
    b"/OQSc4kYJ/jrp+byM+AC+Qsyc/QFHcpXjuNaOT1vzt/FsPPkeomEdfWWshLI5XTA4VPqazZhCWi5zCgSKEuf2qbOrrrEqHxS5EOG"
    b"bQNGNBLv8rsUnyB1J3nBMuEjF2S3N3LT5onPTZbGN1NisdFyC+dvAhMS6+T1C+3bjtyv3Tp4J8lewsbjQI14xSbOGn9A4vDEQVGw"
    b"K1qGt5YZBi8a6ehvIX4lVS2DPDi08wnUN8etLpO+NubLYLhvRpBPtpam2tCtRM+ikc4wDVIoJK8dN+AR5Djxp62vxlgCevymFN0O"
    b"kPdDUEmtq+7JBgkNFgcGrKtr0hDL55Abi/aJLOrS6xQ0TQ6h4DicK2hdWAsFy3aw1/BkqCCDMqccvgZ6en2hjxWVEXCbgkBbU5Pl"
    b"cgY6MzoJ+TIVIePvBUI5OJ1JTVaL5SDMCrkloI0wzl43mwxivThHFCFTb/Ao2YlnptFTOp+tBllNhrDOwLRBT4mQ0k9rMAVPe2Rj"
    b"LSBmHiVDH3frk3gzyuQ+TS4xwdGK4izJ66sj7ENO/HSAOIOjlaHRYW8wVL97SCncjEYY/C4omxGNRLu81U+tAac2VR+qSv83zz7W"
    b"TOeVdfiZw574Da9Nmyt/o4ozuawTdaApBUa8+WQl84bdhM3Buyr9pgq51gV7qEvcprz7+6aXKe/iPeqBfrx0tK4enQc+hquojCdG"
    b"xrQTX71EOV17cBshaL67IdUsIPQAf7b+4mzt4mOCmPqUr1oQtJCOfMspFgOK3LpiUC7h4Xz8MloGSSGrJRFpk6aPFJ3W6OwY736l"
    b"05uaXB7YyejODfvrf+Xh2pJMBzdkmfTTqCsSFbwTScc6lZ8s6zfsHjrqoFtidZ036pbyuyiYLA+hLJRgCSNKhcRI3ZxuWj12WugC"
    b"PKNqWfUyswLFixMIavRvCqTzqBsxWb1yJSyDHyErQSpP/UUV2Pah6LDnNYqHQCPK9SE2bHg+GRhi0NZhg9c6L3HkbU9exwmnSPEP"
    b"vpGOIiwpWc30CqSFzM4bVLm2ugAy1etV2ZwMaXcCnvcB/nvPY0vhfkiW1W2lXwO0dgVAc9Q2MhaAbUOKf944r6ft10EDK/YOHZlM"
    b"Y519kaii+Ll6nccb0WAUIB6Wa2APW3BG5sMriIFKiEaoA6Iva0/P2JfIQDS//xpjyC5+jjSPtd4LP9bOPa6dX1JoXmqCjRupfa9l"
    b"4JiaaNW+sc8DRFMxYBzLpjVyxlgvm7zO7sSYrqCSlEiDSxpzBDhPAJcSRhsTsn8ZGg47kEg8qI2rDIWbbnIJpzLZPhtL1QlRhZV0"
    b"yJt7kg3WLpta2LquGhLpkKfVSMLbPIQKyBage9UgHBnBqEcbKQ3u9KBO9II04yiy4ScLU86sTtuq1ITbtCqhgYB4UiSHllSSo4oP"
    b"VcI/QxavLmYZahn29ptLSKsTL57gLYGabc5dbNy413j4CK1hf7gBXIj7Xk7wJ0KbAASUsMNQW8GMCuxeFRUKlU5od4t3USuEo/fo"
    b"+/rs3drFu+bCefZiQaMvMgsxTzyo/2NlfeZrSCbNcD35hcTGDAMBQOkMQywSb5V+JzTJzNqHRYfkJy73h8SSQuRceSMAaeVB6mkn"
    b"hKxjgVgFxxTiDTRhz3osZOeSqV38mjVA6nyYc4+E45ai//SvKuRnpoSvN21c9drTc2KS5x6JlUHaWUZG9XPHsyKUipH7NTooRcPU"
    b"37wCBG5KOzT2W8XJxYqmQj6qYXG56+R0CO9mNdVCesPs0lDdC9hbQcZkNDPG5nMAYq5fQ9CD2vyCOfPcfHlRgkDONF48tLVhiTIc"
    b"xC6NmN2AiULxIBLbw0FduUEpWBXeb5F26QBSLSebKLRSFVs/41A6MVphzKUwyhaCHcim8xA7BfjmqheB2yvixa/KkTsqYFglvCHI"
    b"UQz2h8pPggjkn14HhKL3o/GThkcqwmGeDj0rjXsXYqtjrtJ1JRGNvjsrPWahFgdzk0u4pkb2e5g4w8zIMzBlbaQW5NvR4iSt+MPW"
    b"KQ6LW9wpQ2EcWEdeMiP4ZFqzqH1DNVQs7tI7Cf0eDg4pfmgoLB0dLhbq5FB/bNilLk0JQx+p7cOhxmdisLmPjoeidx7aAX4x5K3+"
    b"opNbomQF+JmtlBvP5jLWuDn5w21MXhw32WhYPKD7O/tqpTAxEGdcHe4hP5iEptLQiQYoirNo5DU0vE5Cnzg4nikMeNT43u59+w8k"
    b"dn704d4PBg8M7npduyi32tpSDaZd4Ci0O7KFdFh4J4k+RkrFktPmoKlSDxaUt0ov9qZhkLhE1wSKpYltZlB6sWT6/VR2UI6/IoyW"
    b"sDTKh5S+CYkg4jm//P367Z8tIG3z2CJjo+K16Ivj5uxjNGC6tGzO3Wd04X8+n6+d/LLxaql27fbaynE4jJpUsX7iZO3cSzihGOMc"
    b"Szi7sH7zGuLwPPzH2tNT69duokUSCG+L37Cotn5iAWOhnVmtzb8Eqa+xcr+ZehJ3MrqTuXa1JjPBOFCKpspO+7YFds6Ug7xIBqx/"
    b"w80hRaEpS+TB9vW3tKm4Llyp2AgbZ7I18cZ5smK3hR5qqL9zeEM1r3Z4YuNxAxExrHiSSOWpToObd5aPLrFCXYfXaxDZiheV9bTQ"
    b"bU5M3rKVB7Ca2UJga8xgSPn6tRm8Ob/yGS5ZEFGEXmGutrwIXJRQoRLurIokKzbYkx/WVs+wogJKazy8BZwtsxvAfQhLvVeXzKv3"
    b"QHZZe3qSa2FjBDS6o6oFtvBxhKI0byG8MDMyUI4uQUxRDG08cadt+w6eGIQ4C5JNwnRok+d6T1tz24oKkUxeEhOumzNt0yX4Zs3/"
    b"pgBbTDpeB1/pcJbQ+XSXCETRYZnhwJOzz+809WwCdQYLwLawlYHsh5PR3W4QUg1ZFlg8nedNUn5aBKfmQnHYcG5Y5Pe85SJ39iFl"
    b"2mzDj2ngZ+I8dXKzUWlkXWOxKNT9Yf9dzglosAuhTf6U76DkyD3gw2kY/Le290a1OfuwQffJr8Ve6DJAh9zt1DjY7AUpIdXOPTYf"
    b"vcTt+XwRvZvpSGvcvG/On1u/fMs8e6Y2s7r2/Er9PJxDp1Ai+ukrEX3j+YoVXQKBpaXukNUQ9h1JXN3gifHkVMblLpaY3mAbObfP"
    b"9BtuH6r+DfdNwl6bWAovTuqOsjoTCMKI0pvXgkzQiow5ViQWAcsvbgOXYxk6Hv4tGEI66J+w7hWG2aJtHD8DQeQfnkYMdVQEneKH"
    b"tuIA15KuSnGrcyYOflIcIVsK8pZLFEJCf0nNpI5RwFvfhZ6QK33YrWR/g1t0GOkY36KLpomL9ITzJp1az9fpCf8txDvItS/6ocmb"
    b"mrA0PBTUZW7FEW+3i1GL64Gm+Oz1prfg1NghyAz/DdPtkYuB7nR6Gr7ZtbirJqXEDTRy7nWUkItG93+ktZDK0bhhJu+jkVKSwUlC"
    b"8F2YR/JdHcP9mzbktxJSVyDUCk6R1Of8xFYr+uwwZdRxyihN/8YC46+wEukU63uj1S1WeNxjiSM7l2CbkURBGXpxcey9YhXtqk2J"
    b"N17W8SZnWIL0SJAGF1VTdpk3k0uN+1pmCRvuJlaXeu6iLn8mt/U91FILlYtj7+NpI4kK5dEml0NwNnlcM3tNNJ95hTf2qrL97VQr"
    b"aGHl6X9oexjYuAaNDsOmImjaWwD1QNClRtrbWiMUTY/4sGVxDIL3pR8ayyC030Jl8dxxRCk5Pms+fLb29AxGz5hfAEkegy4++QF5"
    b"pwffrN+/ZK7cQRFj8WsSQ+ZYylg/hqBgQvS4dqO+9BC4IJQ+Xp5i5so2zZjCXZh227hXhIn8FB/FJFkH/YCYBJuCHooJDIzApco7"
    b"z8RkIfsXff6cZroKnoqVPe2GON5gFhLZCrUB+U20cyesBKiNOtLaJaeCtThZcoV4kPeMsh5aL9xrvWmVPN8MIaUlTImQILec2C0P"
    b"cQZpQD1lbJHlkngjGBI0M+GEbxvRSJeXFMOt1m5Y5WaYLHmcgIU48r9xoos4Te4Sp+LWjEBCNwHz6+pUPMS4hHE1qtyG3Z6Kv2aP"
    b"fXrtrzzwGw/qv7WDaYWKeVJcfjGN2Ky2gyPsVmaIUSfAQNUnTjeefM6Bu/hijvUJv8x8KkK1kisDBiQ6+8K6+NXM/E+LatZeLvHF"
    b"Kin1juGul45+HD1F9QhAvz/FKcDhCsBOAArAkW6KoAhIbneJhNOqPqHsz5YEFE6YrRApL9gStKeQUtCFFI05ojI8fQ2csaPwNvTB"
    b"N+zWKC3t6je+W798lqbMaWIPtQshh2zn+X4ThrfxeBbj/c3OwWgD7a1fv01KJzG2PKr6UqpG9VvGjVm5RIs2cFg0XmV3ve6B6r7S"
    b"5hvsdFpnoVnHI21LPI+BhO85YHOB7uUy7EF9KJF9Yy7s4bxuvnFs0CI0URj2c+VPkBOLYPJw2bymZz8dXa/ZYd+2TL1u5V7njTZY"
    b"lSlWI3kbufAB7KDFCfvcmWJqjKX4kGO5vXSanOCzyHUOJVogy0q/fGmzt3LXYmGdRHrjcYQFrUtXXuZIPIqWU8eURwpbX1NwndZY"
    b"SX8TZAjL8IIfbKUMTnvKFkyLPC0vmKhZhh4GR87cHImPVoTNEIP2im1FBDnssGQDKsJGyQ4q4nlL4dcCooqNJz82Xp0wLLI48K9t"
    b"ke5v5WNZbR8vrTj+aaQp5AoDpx0oDonAx2GvBZOuJz/A32APHO4hPztTarxqYZrzatHGNdaufsum5J6nfyu1O+vdplb7lmGe+Fy1"
    b"6ULTC2ZQgNF59P3aq2u100ct4y6OOOlp4rXptSzoLEueDYyIpCj2esZ8gmwnC4eCrYoOTsnBOvu09dXvkhF9LBGzzRxiWx4lmU2P"
    b"q0bPNDC3aoJdVYsHZRWap7HL9mfaG1NMMc2kQlESD06HWjZP0erRAKiGhCPxVDGd0BEw0cYxbHS/LnaDHrNmvJjPgISVwjyVoBYY"
    b"mk0hDUyxXyRAz9ratVfmtYuw6s2FG+ReSffuixeManKERHpCtLvAhnAIjDV71Vw5D5y/2zYZiw78t1kjN8fM02aAoswRdqkIfDcZ"
    b"aA+o8Q9TFQoz10KcOS3AnEQ3U4Y0EFI1yv7TKOocGvYKdAnvBCC1A08rk+I9mHL7Xjqxzz3c/JsyGdWqcPSrCCf8yQCuAIqv4g1e"
    b"VCXfFYrGKgOVvpv4cMdeyl2tAh0IAAOUa0uXk/kkxQGvr9ysfXW1fuxB7YsHzsvTasGzfl2ppIV7VR1PWVVdRTSPgyBbhKSYhcB3"
    b"k7kc1V4oFjL0ZbIA2yVbyLhwALgd3KFqwcXXC9huq30eULUe6nXaCYKAuLUQFmSUAOqzCYMfXtRrx8XakLf0jpNld2AogKtAouFW"
    b"PWwkrDQWnC0NoyudQlezwm68JfJvWZnrOIECosn5z2CuASmYCtjUYaApz82vJGCT858ahbG2vMhWDevHXphHr9TmzgqcIgsNkJSS"
    b"n2H8dQqprcEEIsk8SwzE7PfANDqNzYUe5C1sJxrLknX6+gm6fXx6R4rnp7kxa8+uq4BSAj9p7iJ+OT4LTSCjchtIyoJiQkNdGgd8"
    b"+/1qfekhB2oHYk6IpFegAQYykBhqQYE1hUo4/Dzbtf/nzB34bi4cxRFtNyzeCJ6jue+Lh41lvDnFMaOjAw1VLp0xj1+2A3XP360t"
    b"fCVjUy9RtfGQQbbdGElZXHifPYNp2Yv/6BXz7BzGtqQIujycwhoWmLHFb6EwnJ7nX9OhxUV2QE8+fYY84ZnVtdWFxs+PkEe7dhtn"
    b"hi1ydnJAIBzac98LA3Pph8gDiZf2VCvam1HdzO2hbgntx04QwPa35tV7cJqKO/m5C8wLg9yAEkMsbpiPFsmdYJ50ZXx3f3rt2Sno"
    b"IrSqdvW72tUVgqsxLMArRoS1NGASmkpsjAMU/U86/wQcr/azHYJ4GbbSVeg7rwH6+klWpAmpJezes2vwj3x+W8r9LFDIaQX7SlZG"
    b"4FfQw7eNjm4BfiVe7d3x+8HE/t3/EzG04tqbZm6nIsm/fzy4b/cg9mOIdjkFCOflx+cGGj/PK7/MpSX13co59d3sA/qllPT0mPb+"
    b"vpr32TX1HS1zLS8tdqUVyi9oBf3aNKzPyIEPBhP7BgldAyOalrK5TJAy/PnPlbeDQ9G2vuHDsXDHkb8NoVHBymns29IS9mL2AbZ1"
    b"9j62auEopwphriEiRfeGAyGXrxr5FKhh0tEVlzYWb+M9kLUdPyE/7Fh0EJxHY0femSJu+Ysv115c5W23fu4hoxVZ1uh4NXPrW4Rk"
    b"prCyjYcqwAYH3aJo735x2aXuyD1GEcb8xQBXId9Y446w7nZeNR66lRLGnF8Mwbj9MjMzvDUgvGZGPIOm/zJzNAwjEIEu/eafz4++"
    b"88/n14Mh2NewfYeGf5k5+8vM5wHt7BlRQqSTLE0C16Qe4EbZRv7Ib15Ybg4kuLDh3Kmh1oJaNGmPT5QPjzb/Px/tQ+szod4wbNi/"
    b"YnBaGJnXhzbzhBqiNsNT+jzyLwrZwR0mf+cgMS4gkihiNcqUJ0/i6Tb/jBmYdsE+0L0sHu50lJvPHsORbHAJlrssxs46zMSl3ziM"
    b"Si8kHuFSNhVOFapHjjQN64StcIlHypj7yPXugqY9JSQXm0wA49MbxoPzSKEt0Glb9nPiijtVMNMbo8cKKYWAoAVamRPg2wPfe8rL"
    b"AcxLWHA1wsM/TRlUF645OfxAlg2GNu9H2vlYoEPNWVd+I+Cboo3jFcxHaOUFY86AicY2I8YNNbYbfX19GxSquPC5Tl1nA93YIK7i"
    b"0DuJtwR0tQp7LonmNGzzp8YlEeb7hSLB/4xtUKrrAi5FSERNA1BM+4XTatWllOuwr13GhkSLh91BWytW6Fn9uQynhTRAfwMUQQQN"
    b"m/INWDbt92JSCyRG5XEQMfirBlN1Ub1SEjhUnh9XjDpgim5dQVHh1bPG9ygACJh4yw948SQIX8BlAQMhfVRQcGssHzfn7qMOjUx8"
    b"QQRDn7+rM2jrAj/PfGGuLPpFhECKxovDunlEoA1qoC/WhpdOiDJLquSHjOezq5QLCFxRE6y6nFCUwoplP3maKAD1rk2C5UF2ghIs"
    b"OnXxni1QdAeHAzgaiKxHg6JA6ZE/YAG9AfkRL0ZYi9a1PNR2ROwwL9/4LOrT25C9Q52GLHgYSHkbttXZc2ci/E1tG3ahRIo4Xa7F"
    b"lirmcplUVVHWisv6+S9VsRxWWowMv83ZH4FFbywDJ/8Z3/ILuBwOnAKrSyaoL/1UO3Obb7LYuHn9xEJj+byyzMQackD5FwuZ4MTB"
    b"Zsg2ZYsYVjBAscAedZ0kQt0aENjUSNTb2XYwEPYwjSsn85WBw4EkkYkABinGUNEUSAUeoN0w61/hZSxwxF2CZY/ofiWjDR8O7PAN"
    b"5xw2MOhPeymXzML3t9vfdtbh0juWPSII+8bHcBgjIA9QJhk76IlsYF/POMOihJoywi2bHtvN+pfhtHUT91qyoqKq2lOK9oLuIfA2"
    b"kk+Wggl2C3WpAbzsJJpypK3emEiICMqr3vwJJMrZe7XTn9YuPl6fmUHG9sFt4Fdr8/fXnt5CDImHl2oXnrHGjim6uCqZRZgIE+HJ"
    b"5/BkWDiJ2JSQkaRn9NM68aP5CG8Waydvr5+7rDpm0c0aR/ZB+wOnMbC3QY3fUAjRsZoZK5YPJXCfuPTv8CdhhewRUM3lTKqYzwNV"
    b"1VbYm1q1SowF77PUTfwmC0g9ijl0E8wcVGSLiwJxH6gHKsy+uyGUb2fngDqiHKEoBKXTzAV4BWlwdi48ggO2tvCwced4fekC+pYy"
    b"suzFu4wCopBACypKQWzkWEPYLrnjthpBaKAXcKPjkM1WW5MqBEepqv7p4HDz2Lb9hUxowSN7sZ7yXPc9+DdoGGOMicBoTblTOgXD"
    b"bEtk3QJ7OSXo5GrK/2JqsjzEnAP5CzdbUQKIy0OWVxuAhynpPzkSohVrEk5Vo0vgCgMbxtEHVNXtEiN0Y/iBE3BqnhBIMM8eI3aT"
    b"XJu8GFV85uJBD/s4CxJLUYjafW9yVSoVuW3V5Ig+1/LmFCvU41N6knjl1lQBC/ZQCjGZFCDwVhx1oWDwiqWuvXcE0fUA9MJiGUjc"
    b"zuxAEvcnNpQ7GolqagFqK614HAlIst3QFdZ2ftsS0cl5afiATi8KORwuqkUvwpjBgYDURLHUwoJwXYhpy8B9N6YULKabnnhJNXAk"
    b"4B/X5qDbIdwNyEteEShm8agB5BUZSzgXLy1b8guLP5ZoY9258IUL2wlbF1VsUqVsEW09lBhoXjG/oydk16Sthg2DIIqSYpt8ZkxQ"
    b"BbYVyP41o2856/JCBN+qEjYCCwHW4LokMj4kKMUQN7wNr9Pepgr6uUn8Y7i/FWLuiKT3XyBxbUD5kUcmIwouW0YTgIwIkehsn63F"
    b"wnyiL566Ki8l0cYuLDj8LBoOGA706FxyJJOjKysg3gFWnNMFy+YKXt8Ym9kaCPKHNMFPNUJz6mjsMs0nP/BiNzanDVGebIynNKqr"
    b"GMQFvpeeA18p0dvd5749kg5nGnc5tmbEzoTPmuUpZ/LJ8gTKydRbjxQpviKFFJMBi8W1tv7mChrlf/rMfD7D+xz5XLnV+SrV8tKx"
    b"zPqb3KnSyOotOaJRMntopeCHH2H9aao4SS0WZCTI+3cr73Paku3t9EONKk/h8nAgRGxDNXo85kclO35qWSiQO4IUWuHTBRHZt/P9"
    b"xN59uz8cxHvaIdK3W5K+GjIzc4imjON39iPFQ6IVQnU4skRKnIRL9RefC4U6XesbbhEaL58ZzQGkE3SdemY+vFmbe1K/v1x7+kPt"
    b"+pdAnffv34eQZswMczAJlvb4bry2vIhhlLiUYy/M2bnayS9xCo8uGF293X94FyM0seFY7dQro1o9SMYNgvOmy1I4BRp3jpKPNN5c"
    b"8mU3VVG//KJx8ntxofn0Wy5GhnKa40hU3AAj3hX9ewxk53yF2yiiYJMfCKwW4NhACDCvPjKEvsGoL/3UePWV1IyI+q5eh9ZyUJX6"
    b"P1b4VsKKhc0cnDCCSxWLE9mMweoQ6tA5svj4VrCHi9+qUSXkrPCJlC9VD1HQB0Uw7ye0Sl45O8VyjMoHezFWKzyAtWkFwuxni3gZ"
    b"BQkVH1Smj+pDALcI80xbDYLPvU/PkK7PSWWCr6/Oaaa9kdoa/rAhm3pbQVR4Q2XMr1O/uKCOxHOXDqYlrQnHe1E5ah5kj5hKfPoF"
    b"HZyzGpjGZoZVZU9IsPjWzblNZeA8dvoE1b46aj76HDc6Rib9mRALTtaePoXNyfvWQOS9pa8kKbji2BNoRo17YW5tdVYarcx7AYJq"
    b"rfBygWiitvBcXQFl9fzqIIUes9EkjKkI34UfbtlG06pZq8ct8StpXbfNRC08bv5F5GPPeXcgEjS9AJXCvtuE2dUAz6khApXgaNJ8"
    b"U6QIZjbxEsiKLW4RvdDYRrXT+e1dO9PS17uQ0guNuu7/HVdSKhGngdXfayRdKdormST0giIrw+BkxuxjgBB87F5bgZJD6gVVS4YN"
    b"PNM608F2zK3zHfJAvbL2/BIwA8yGGH98H5gIEaVSXDOsz8wgLbl410AOg+TGOXQGIQWownCcBmrCFuN6JCs4UZzhxDOHuHl2QLFS"
    b"1r05XN2GVByxJ1lxhF1JVqs4JrYvZrzZESgJh2omHpCnHsJt/2WyWM0EJYRa2KgkRzMDLgwoGvE0eWpbk+pnTS46lsACDxbL6VC7"
    b"al3uQtelkpuNiGNkOINDyKFBEo3EsEXw4E2w391bGVUSlVwmU8JQOiD3BuXwb9Xcv1qsQ3YBm6cv6ZFDCTFcFTluFWVde/DSsCbl"
    b"jRiCpC3g+mZUQVi3yGDSd/VmDRfzy2/rZ5b5Zm396CtzVng649r+8TybayrreWNNhgj+NGHL8FbzlVudCS2CtxZjSRQQqF9/ADx3"
    b"gBMyqiS8UjUQLK7CQ+E6VFK2mk0RhKDFJ1Gp6TH0FogLq8AsA1dtCOvv5t4XfiY4nrbwzW3gPRQJUxzWzdfg3QPGwsvA3cMY/S2j"
    b"cflK7dR1lHfIRtpaEvRzqXHqtjARvzpv2EcDBsU1Fz9tzBzTFEi0DJqeZpb4KtaOnDdFiu0j8TUWJTcHekb8iEz5q8Vl69GbSMcc"
    b"+YzTwJ63ytpAalYUk7gmK6lkwab/AxxhkA9O4Agdh5M8Ta7whZwqIzdu3l//5kztzF0B5j5/X720wzm1Lu0Iih63uQi8oJ5NvKd0"
    b"kUuzZ21BbWkJieo86OOP4qAcZ0tWFN9zUqg8opGDzKEmDGYZhpgYrqEy37cK+LCUDHez86M9Bwb3HEgc+NPewf28cS14MmQNWFdW"
    b"5m1LZeHvko4AKCeGyPqwLWPiDXCwXFLP5zARnnKpidhp3+3oF5eQFy8rS83uKN/slns8W6206jb2qy7BXcHJlCvwzDRdgGOGMM1B"
    b"yDvemI934utaNLaMsFTI6yaFLtu/aT/DwiaB7SVuK34Kr6xC/k1DhDV1pnq9w8Tbp6olT6oN29nco0quQ+fp07oJA+ZuQgpKBL4a"
    b"Z9mHOD7tfgJes9vm+GQBPTextKFKtb+CzBq8HP7VKlg8E7DUEBdoaWHhu98xQ43xOmisstyHCuWxjxUfd7A3/YcOWs+fmc/Omw/O"
    b"1n9cra9ehwODXRiNHaWS0Vj+rPFwxWgXqaSENL/pLcgpf13Z+9H+A8Z4tVqq9LejIq2rrVAs55O5ttxfIqN/KRSnMjl0Emmnb+1M"
    b"56qocBNf27Gv7YdhIR1pn4q1k6sT2Q8U0yDUjUzC5s9UKgnSw0VAmpxI0A4AFnF96bjtkgbyCoZDShRHR4HaJZBdh1T1by/iufnz"
    b"E2BpgnjRJUsXoalJhsE/5OU4NBwRjYpkpksIQaiURijE9zl429rTM0ZEXCVEUI1nlQsnsNERrRiMpsnVr99YMVcWzcULeJu49JM5"
    b"96ixfJtfrT1dAZ5z7ek5ESqgAB8JUoqCnFbIJycmqWHcne0g7Mt6oDWN5Z/QEQ2E0rlH9fkT5qOXQv+N01N/8JI8X65AVTxV6Hx3"
    b"9ljj7vH1m5/zk/VPvzFvXzRnH9RvfwXlwek0Viy05zPpyUqSBYPGnaNoVHJp2ZhuyyXTxQIs9+m2ZHlssmK1BJ9UKm2V6uQIVM6p"
    b"MEdHpwHSiPFeBtqfyQFvSdnoValcrBZHJkeD8S7DfHCx9vDnkPGfx7+wityfzRcLbd2d5D+4+hm+M7q6Yoa5eGntxZfQ1PUH54Bf"
    b"bTeff1qbu9BuzqBtKbQY0+0Y3N8Wi/e27Xx3Jzu18T8L/Nx8+FX9zCOcwPezcJoZ9fk549/2G+szZ6EljZOfYryOEz8xIlvj5ZeI"
    b"v3D29PqVxdrVFagSirGGot01FAinOnuvvvS0/mBe2CwufV17cEvEwlh9wbNiXr1nHPiPd4vTePlg7BxPguRdOoQI2MBmN469YLNG"
    b"ENy4A//aPZ/Y9WFicM+Odz+gqxzUbWpK1plV8/kMCAUsGqDz4txlo5RLHsqUhXehwZBZGOmQyAKV+D4SgQFUcvvt/wCl+x+79+z6"
    b"6H8kPkRXuI4o/LNrpusJ9t3kvaFuOMr84Y4/igL2E/VXmk24wejUD0+tfUfU7I4WYJvNpVjCrJ3/iYypuHDh+tdrNcmGzaBuskUM"
    b"iEW183O1q0QpsWWn0Wr63L21lTNonjX3iHH/cNNQOLz66pdATWUd7+3Y/YGoqLNLqwLySutWzoJOmGdOYTKuhlE4hEfKdzeEkurc"
    b"0dqDVXPhJFv18CDt3pP4/Y69ZEkS7zU0SGDMSJ3hS6q1Z6fWL/6EbYXhe7QI39evnJMdo9U7f9L88dH6pR8Evbh8tvbzUaqFDAr+"
    b"x0f7/jC4j+ZCnUZ0mCGpg3DN7PkkCfP0+uWFtRdn6l99h8hclIwK3Dd4YN+fErsGP9jxJyivOxK1Cvziq7WnJ7lq8+wZaCHM9Nqz"
    b"WTUwOi+tHbsP0Awa3hPYeLJcP/c9rxTYn9wyjNcOEwVr59Hn0G0qCAZwLzRjcB8uaDqIZUH6PoD9aggiLaiY+eJmbeZoP2mugTxM"
    b"lnPwF44QHrKP97+PljA7PtD33VvG+s1r5q0LiFH2zY9IEWLxnkgU/hfr7+vr6W1PEvACHLj3LJzsxsxRSGvpHan8/bt3IThBPzHI"
    b"Q6QMhT/DrDLEBGRso762v+0oHBpWUg7+B4hR+9WktnPr4BT0XUmLtj37Pd1fsc9AFvz9Y60EO4h4oOWTHKjBXWrtZFGl1Ln/wL7B"
    b"HUB0dh9olmqD11hrYnAfzXJgEz2CsyPxh0FcgCOHQDyMjJaL+fHMdDCQ7ohlOnpivfHe3mQsGu8ZSSZHuvpGY53dyWhfsi8VCFn5"
    b"d/+HO3smCXQlGe3o6M6kO7rio6l0vDPTme6KRmO9yUxXp8i+f/eHH+3xbsBoqqc3E032dXf1JKOpns7eVKYr1tXV1xftSKVGox1d"
    b"sSg8SHekRkfjHfF0T6yjsyMDje2Ix1JdHVFZw4d4iroLj4/2jEJO+SkSHwBq5Zk+kxwdiadGM71d3b1dsb6Y1YG9+wbf2/1Hnzp6"
    b"Y+jbi8k+7kBoyuj0e+IfcbZtTf4Z+z/saJqAh+/DDh79YHS6p6M3Guvufi8M1XT2xTrfjb/bh99jPfHOzviuHvy+a0fvjmh3NOq8"
    b"0I1O7+jrfq8j+u5OytHdEevo3bEDvw929O4aHOzchd/fjb73bnSwc9Cy0EznE8DW5DriwSQpasPGhK2wzcpY4hPGFjj5YprWw63y"
    b"R+g2HihVUgkGk8a2bcZEyPibAV+3bzeCMJJt8CAUUnLY7ankOxKp0eAUU6SwMZLr53kJI1WyW4dvuREHSVkSHMkNQQJg7bIgTXUO"
    b"Y63xTqpWf4NKEnob64a3yji608UpXS8W4nrXMay0n03PFKVMd8g2SftEfR42unsVTcA0ouAEDw59gtJY97Dx/xv8vQ+/KtPDTzuG"
    b"w0asSxs4Sy1i4dBBkVrW6U8ok/thvAMebvJC0XNUG8N6e0JW47rVrgvryRhNAryXfdgKc+AcIWUkujvFCCVhisMG4uKEjQy5yY6F"
    b"jXHL0tidTbkuoh3Z07dzZydsaVyan6AHYbcAHZzu2dHb07erd4etcq7E6DbJ6l9Q3QEwTHGKDYYYevZzWIOfGJuNjrg67jgeSrFI"
    b"G7BwbYy5QFVPzs1zqKAQQTgJOUfgv5QeqRo9EjPweBT+G2tiJkdlBHEHjoh9tsVI8dKnb+5Sgxl4MUpJ/o5fx+w01SoOUpAWexot"
    b"tqB3W2GCYWq9Fl61ip0PQqlbYdq20jBsxRXgmTpNUw0Tjtd6qbA6XPCwLxTG9QAtsM0faT2g8zR6Z2oZ4GEMc2RQMQ+t0AYfHmB5"
    b"Hg9jPa4NZGG74TxMoV2lOtPBEXoaczxN0dO442manmrEQafVwQyl6HTkG6WnXY6nY/S02/F0nJ72qE+HdQpK95yCbhK1pG8Ce62c"
    b"HROGtJiKJz5fGRPnX7JcTh7S30jSEp3ujcqrjUqmTAC+QSpuswEbEwkrq8woeEJXtzww8Pc2mcdeufh4K/DNnVY9mekq1jMS+HM0"
    b"gLeVmKJNZgyFnOmARZpMVSPkehDY/u+BMPftbaDYnBYxVhnU3zpq7aswhVzjWEC5pA3TKMyUIBfyUApj9WE6AyCdBkARECaveqN2"
    b"Q6OmFTy5qZDjqEMMuux0d7MJkwp5ZWpDQ/3dw74sCLTNWHuxgLqBV2frDy8C8x0cz4aNXDEEUttpIGX4Gnhwz9xW8ya7O3OZ4Ij3"
    b"8VudLOXEXObQtzs4gufjMJ6U4qDkQ7ZXeRIXx67yqMM6p/UdOZ61yqSTRMnS5Sq3211uj0+5kisRw6FMBvU2cbCcrWaQ+aD+EcZV"
    b"v70tqOd7rHiCjrNJPdfVMNJBpB3E+fTCuvmEsXHxKOjkgyqIFMd6H8QTtjPE7BHym2ojp7s7kVMTjRsR35wTIjuZxHLhYIEPoKvY"
    b"CPwBdEwpMZlOt1QmTTKVsZXKsGeJatlKtaBDVozNItDlQ5z8fBqHHOOvUjRIrvATduOA01Qa59fN4N+TLpL996ROr50cr9bnguey"
    b"LhD6YMGibfh3s6RWhBo+AOyHiw+mUefhDmlJO+JeaWOUNqqm3aYl5Z3AcwlLusAHvFxRxEsXQp4sIe9LTqvkjDbPqXMXePdUQM4z"
    b"7m4QF5v3KDa/QYOiWs5Y85z+WxYmstzCRCr0U049rBCgkW2GnF6eWSybTor/CXI48ZYdu3b2de7s2CEff/ARPY52du/q7ul9V6Xl"
    b"qP5N/HUkWw16iVCyE3Y50OUJ7CrtlwmadEEO7CbgsEzQ6NOoxFz1scYfa2TDQ00u4itzjlDpeex1AhermV/lSzZ7jCMLJQxlUQCA"
    b"RdoR8kiH9Ah+Edo0pewYbppMKZt+q0ZIUIQF7yryqJ9MC2Q9nejXD0WEmlo2E+6tY3aClJ0mPI7sYYdKJXTLDajMPeKFVPlQqRos"
    b"Va1VR4Z81vgrC28azn7kpUtVIgkly9/PMQ/6JCCujc3/llWJBQZgOhZWbT7Lve7Xir0uyQXlGG64LZCWmgE/Y+JnTJmt6ZgyWfIT"
    b"ejAaCmuPlYriITHxKjY9BmeoamuehiG0scIEb0F2vrsTVegXvzZv3DdnZ/14FBevkkSQkZGUNT00J4JvyU5ZX5twWTJSB6Zw0ukR"
    b"G/YI1WXv7tj5h8E9u5CoB6i64lg5WRo/FFB52xSMw85saTxTDiZzY8CYVsfzlQhkF5aK+WI6U4lAf4PZqVAoIhpeLAddEFvwKjJZ"
    b"wvBuzPuhiAqPRrOFZC7714wNeuVsW+kQl5lGCGBXp3bSO8gTKWQOsqWP/ejDj3YNJnaiNglaJxunSAXCFYzbs1kTahX77aF+O1Eb"
    b"X0DbOaT8T+Yxib2T5QxUHIv32mZwwBsjA56dGuqPdQ9Hcp9MAilDFQoJCKoDoC24eBK6aNhubRirtls7kisSUDKthCDL4WSnGkZM"
    b"uYLx12yJ8g1l+7PI1HbjRoZ2qdaTNNfQDzlOCSo0SH91yzYhuEA6+7noJTzT5AlqD0Gs2iSoNJGq9DQTFShcfLfHWKtF0wRtFTUM"
    b"FYbR+qCw8faUF6AGwojO3m6+L1O5ZKUCZDW/F3LYxmJ0Z4PXBVZh9ecX6l8fNS/fw8s7upAQN88LP3I9/BNdIJ6ewUtPvPvEQg15"
    b"6SmtxGzPmkS2kK0mEkEMauRg2dkOJDcaSYxmM7l0Rdx7aEFJ+D3M3oj22ip/igqGnZGeFkpTDLdtnfkB0euAd42WWADZw2hXRkhQ"
    b"yRwszGgo5I6MlRtVeoaNctXuXA++DaAuyfrtvdy8hXFqJEP0W4WEyHhkg9ZWXC1Fq4N+vLjxa6dSDtfEbUDLIcxLlAjoZlDC8oXs"
    b"2srJg28yMj418uhYhZfco16ZBFHJKvB1OzQ5EqkWE2hOoPZBPLLWrbKz/WmdRe+wYA5rD8sJzvnMKBtMKat9k1PPO5Us4/pDQ1As"
    b"AHUnKMRRpPktRo87dpiMQR/1Ct2hl4eLuoWIHzgqZO5nra4haPrwhsUT2ick9wjioZBaSuE6z72Iq122IvFTLyYVK3ablNALvBmx"
    b"L4WsyyFSiY9ncxmRajsC9PZ6qwc4xWZMgAIRftj6J3rX3k7ZNzlyqhk3Jt9sydJusB1IS0wVc7ylZDqdSQdLIz5nDosZLplkyFYh"
    b"afeESObChu/L3uYcvX9GOOSaFBvvlLE8WmIYKGD4CBt5q9xCkTTtqP6LddvYLFW9/4JZCtqNKY2Q9kxroHgGu603xHy0ElrGoY9K"
    b"sQBhAa77pIkNu0HZPZc6rQWroSOZZMFJyoDiCrjVEdE55j0wrUK5CJGZIqLKi9qtXisHWVbldpZhgSdHtXmYLAz19w57zkYvb/bJ"
    b"ghr7CfJbWwjyZunCTLQCRMTNRu+wrUGTGYDVypQrkmVGaz29dzRYkBAbPBJIFh0gw8lKprszMtLdKY4h/f54q6ckotzRhw37wj1M"
    b"tQPjn85QUer0sC0dGQ8G6bvwEyPsTvyqTxGejMK8llKrNrXonwCvI2RnWEHb6WDgHdU9SWTGj6FYv+XoEngrgONPB7ZX2killANh"
    b"GpKhOAqr05o3aHZVZpWptgTc6EyYbgMPEaYsmFAWNKD7naDwie6uAx6wpmLOIAvr5TEtdDAkRRfccMZ2I8ZKF4mbLTIFXJulkh0r"
    b"aJOBtoOJ8cy0+FmtCL4gmU2Lb7lsKlOoYIgGfuBF19KZKUhFSagYMhrP5eQDsvNALO1Cmo9w6SYY1ZeAGFMlnX3kWc/Q7h9+FPMR"
    b"/MCzDmX4WGdPZ29Hd2ePvScS48nKuHLzIe8odPMIOQAhgXTCv3g4XTnFjY6URHiF+1RDL12cHlbCy7ulGpBQEV0ioha0H0amsNux"
    b"aE9PX2e0N9Ybggdx1GXAZ4c61EqWCqrKYGJD8K0rbE8a/u5WJ1rL0xP23s1hI4BUKIvxesmIX8vVi6+jnRH8f1dbcaoNGlQuoq08"
    b"NLAPWt4BE9bZ3RkNRZDljUWFOEzXXti5WFgq22V347g84X1ceUx5O8L2fIvioKP25CjpgQOOdYXt8RTDKEYvJkaPPslQZWdPX3xw"
    b"586deudQeLeXOA5fHD1rKAgMFQVl9nT06vXGO9R6K1hvYA9S3H8LiOp7Y33d+LUTa+6NDkZ39UajIW0Q4l1h2X9FH+w+CFU6TKyS"
    b"5Gfy6S652y0OiE4u3mrjOlcR7+31PMowWCLdeOCNI5UYUg+18SoeZANAwWWFqFyzBQQCBPO7h7NV7FCMuIzjb9ptnPVIuY6znvnd"
    b"x9mKfytpp1Z+l7v8bo/ye5qU71L085lDWuQh6jlyjvSlV34hro++xaVByQjuiF46p/Il4pvoi1C9yvLoWVy+7Bj2VMx2qHfB0304"
    b"w7br+nSvriwf6dVUr9ZrvmGbhrfTfY7X8JQaON3Ll3NZRXkOzZL8zbRXsdOiUFUn24dqel0q9LmfFIstmOUguCz2fUI4ZkFuTZP7"
    b"Smq1/4WlzaJhYNrpXvu3nJVIqVgK6jeC41XXxmMt2rgujlXKKe23thkUqSQdpb5AcnW52j/t9Wo/Uxas/dBjxaonuaxBLz3mUXrc"
    b"q3SP/cbDko452h+LO6ro8Kgj1ulVSayrtT6gLKJX0udVR9SzjphfT5rtqfGoIClZsQQlUZG/NbIiH+qERT5tRlrGY2o9jjpiXnXE"
    b"PetoRh6lg7G959NR7cYrTXczStB3blQUNj7lJVIwHrN+qrcztJzltseClG2P1cht7y3dOmVFzGEJiq6XsRalSHE8Cp03cg/KGdn0"
    b"rmVcSsweJ6z05k03VWXDwnPbK9lKbcg+zL7P6dcT+qFcD6nfVie5qRORpLDQCYRec9SCltjgFBYUOQJZ0k51JC22X1y1BAOb0230"
    b"fwqxWq2oxTHj6tKcStXNGPnaUhVovAcyJPG5Xqn5nsN75pFbzGVHIjCHQS41FIHJTGfHMpUqAmLa6mY/YVq2AS9HvKRilMASAqRK"
    b"k8SE05244WtFoPLWMMkRhzQI9eWaE1qQsVhfPNaDtiAapEVVIvUoKKBipYJghO6cygCR5K8ODx6wpIxQZVHRVS1gQ4Dc1sqZv7RV"
    b"s6mJTFWgjRF3H4sCzxtWk06Ml4uFYsVKpL+lSYR3XovStYDCYjELAXIsU8VvI9kqCCwiGK1iVxAK6VURmy2qcorTLEmjhCIqUmu2"
    b"ZjNsWOCJlvc95uvf5IAvGwpYnn0Ey4pfND6Dk22sL2Vfm9YUpdSRoL709J0aCATYM5W9ktDLaGnFfHiFhS2+3VK8WHsiHZG+CNrp"
    b"OS65VD7ZHmGr5oHNlS3J1MDB7Gh2S2o8WShkcgPT2WQxn03gkk50d26BMR4gJDs7+xbgM0kUHSDPN3R52SIlVNyGAz0dfR3xLarQ"
    b"OiBbqBYjmlHKJauwIvIDQnLdUqxYXyuVfHZ6ICmTYnjKgXhHLN6zd090506PwkZwnYk+bMnB8ppENIq/jkOhiFA00NGJ30TTBmKd"
    b"ahH5ZCE7Chss4dGZcqZSzE1WKVM8Gn073t0T3ZKGArviUbUMvnj3KmG8CCUnR7IDyXK+u7Ntqhd6VU6OQSK1c6VxlG2VAktTCXbJ"
    b"EsVgLLpcFoECEoybNxDdUshk0okSVFksJHMJC2hhIKYVRKUkKkWCjxmIbcnCiPAwo+Y1UUmVM5nCgOgNHp7WMlGvlBHZYcoil5Zr"
    b"sqXlQv/kvDylHNRVp6NepNaWUYfYnQNJJv8dVoK4XGDXY4T5v/hT/duLuD/IAQ7dH9nrWSI741jAGJOHcbYwWgyzF3JIw/05hEOi"
    b"U07dKRujkujoX8JLWxBLaxycIGE46rkMB59OpCfLhI1IACEOCDOnY3eAhjAoB1SFElNopXDlhlmdLKcwT3c05vGaAgD3G/Go9o7d"
    b"/fvUhzK6qYzXo3VIvBWFdaj5yOK6nBA0BIFRolHtfbHMcCkKSRbqdCsuWiUoJsIr8hkuNZyJarFcGQgGwgis2R/w4VNY7zfgRWtD"
    b"/mel8HVvE/1zgVn+zoDulWF+BrgupXsfQ//bdowx6C6OeoS3dgRpo5ow6QuVGVCHRrRPmvF4szPMyWiHnqIrE5ctZRQxAhK6YHNl"
    b"A4gCSDAVa39nc4U4Q+n1HEY0DaHoE1wK7AyK0wjPKtVKZL9EhbTeRqrlSdhymQIaq9AUcqyaXHEExB7NL1LBU1f9KRU09bFkSV4a"
    b"CdffNg1AHX5qJWpaf8q93XkD7QlwqQCgYa5fBWTpdP10RhSAE6VULHD8CByvEpwPQZgv5n0HeG4lyKr4tEE240IdIhHvcAklZJFB"
    b"+SXkEZickS4/hPWXLYw5oUtxLwXswNsg9+EFtgoIlMxCk98vFsbGJot7c5Nj2QLBuAcDKoCGQefe5oohFpKzgrBSZR46byHmWVB8"
    b"ghQkpMhCnyrsnmf4PkffdNBPR5HaT70Y9ZWzOIHpJ+HpFSj5cvEghcZRMttN1SKM9zfHBbWr3CjKB29d3IjFg3J86ZELf5CPQRxJ"
    b"if5hJcdYwmJoHeMgkvoMgeMuMRjkwmTBjEGuYyVi8kAo5IXHpYyGfovo2XNWAbi6w4/fvDt8/qJ1HUOjUKHqoay1VaTOVhwGYxuU"
    b"pBTiIkKirrwUD0UxntCpG8ZTcBZo66KRc3QNHj5886GjDeGDpk/T3k/z6mB78hJqNRq2m+rkoXLZCTyQE4IfEs0FYXiMYVw1oFXK"
    b"US7mrBzqBEhuDN8zH6NhtApyCVyigz6om8VmJbVNRlylZzZ6o6VVQ3yEuT59uJlRdY61YF0daemZx8TYPPtoppoab8K0t6IDcfgK"
    b"oHGmQAFi4AsSfxFrRPLhc51G48myhOY73Xj5DJLg37lbtQsPLCwfi2FHWD9i5zmKIhp9Dh2mFWPkK0eG1XB3Ngsh8Q1skuw00CT8"
    b"L4O3oo0QdzBbSDNmJqlqddQWh5rPgcoibo0IpysxkoSRzdh7q1ItljR2R4+UUiwiN/b6YHRONJINkca4Iuvk01oh41C6zJ3FoITY"
    b"7ESrzxUJCjvqYZoHvZjQntIAQVNE2UMUVpVq3+qqZdhZCXXDk7oK/mkyp+IAOoH3SHTCXlIjvEHgPLlARw2ql4kUf8MuUK7mfLjz"
    b"n3PuGGww5d8WGX5dWfT9zQ3fdPgPPKGhglCrnQ1iLAQkOXAWtGKVKVYyzgbFBqxMjuSzVWvMhATR6qA165l7aodff21wc7EE0fBf"
    b"vzy4oAg/DVp8etf/eyuABj0h4VFdoQPYqgvnXFW4ELnhGtzNxs2O4M+ebdOrs2mr17ziGcBMuF9ptqEYaYiGmDkZ5hBcQ8iQDOOF"
    b"Tlc0Gmo2FVjEhvCSG0JMajCTmkmnGzRTYa/whzup72IlwD2LpWQQPo5P1ASJzwXY/ybcp7sFUdf7t4z6P1aAiYATgbkCwQbM/WgM"
    b"bMe4kchUPPkBIcOuIbwZAmRduymhBTG4jHl8Yf3iw00+G4ZAMykIh2jEdi9jdOX0di1o51mv/97KLpnqKmUPZudxpmfbPuAMlqyf"
    b"oOSuldNDkMgDEbvlPhQ955+J8fhkFY5fOOKT2Srr095YtcEL0RlxebrfmObN4x/Ejm6gD1aCCp/m5irNM9fNu6csJtI8e9+geEKN"
    b"F9/V5s7WvnhQO/fSvHyvceP0P59fIcTI+t0vYA6QmW9PFXPFcjtu6GZBuIWcbkUd/NfJ464ZsDadJZ/nK36RMFraUI49pIjfVg0s"
    b"Y/96EVsL1S000mUQt9LBPPoFxKKRaIg+4QsiX7PWNOZ9WRqgqcH33T09PXE0DVSlwiPOONvqPW4VVaBT6jWZfY9qaQ0Jos3lR4MJ"
    b"gxYuHI0PqrSFjKtWAkKhXlFYlSfgDMPJcIhD9hb0a4ZV9RAUS7hsAeqyGvpRBN7sl+JggKqC3/TZzLshUK2iql0iO6JYSGuaDV4V"
    b"LEZbSs9Msb7IRsCzBsVCX6EknlSGXkVYjLLHThTgKVwKg2RdwhQPN75qR3LVz6B2uOzDuH1TGY63IlkBj/gnp15hbDNFFDWf3rEC"
    b"EcPxYS4+4lAIfE+KtSAVwSjtP9xAmMqHp81H35uzcyyZmi++NOcX6icf12aOWqHXqCUDBHGIII+vXtTP3+Y61k+c/mXmNMZt+u6G"
    b"hXn5y8yCBXuJAJEnFmoXHgmESgF4uMQh3QhhE++zCGRzbXWh/tljFLXlLHMlVgwXc/Fb+dZC3kToT0rCMS9EgChGl4R+ffk5Qp5K"
    b"QE1naDQbe1sAaSuuAQJe27XNDltrmCKoyQUcyGcrQEjHME/giBDHxeoQddi/3TXZK0mN8v3DDQzbYL2D2RU3cTCZGCeO9M8wKmvP"
    b"r+A1YCzaEY3GcLjm7td+/rbx0zMe9Va7UChiCEjRer9tTpQDfZibkxuLKsC+tWLoUl5BuWE7U2Ix10qOUWCdx2nMsCbkZhzXH+7C"
    b"5DkTMrZRjdqVCJcnQ5MFaTXbP5ViZNRgjm4S8vSZoOQtkxjmBzPpRKWUPIgaaYvgILHBipjMZCsJW2Ejl4WVT2+IrNMB4Rl0xPS1"
    b"WiTJMeXb1KRwonGshnGGO4UlwrCaG/JgVihbVRenCcMtSsFqvGRvFpYbpUl+uLGI9Qx45kDQ3BkmVRhvkWM/XVpGSNqV4yomLgbj"
    b"eIAxtHFnffbKAqYF7nvt6SkgbY2HK364/AHehuQjhE3ENpmLn9bOP1o/d7mxvCxf+ItSTSVx59WdjrXrL1RtzPY2DVP3XzLHyqg1"
    b"meemi7Bl1YLgOLgQpHueOgIXfxRWMip3GdbeY21msJosw8YfENsHr/wy+WKBzswQO5jZUBR0BmuCmWvCmSpgQhJj3jQalcZSauhA"
    b"mXwmP4IWMjRnviyNg/XTo074nFtc9yZJhASM8ZA0sRh2noY6a0oPi6M6D2yZillEuBxUyrYCP9unuBU8Q6AWDe7bPbg/8d7uDwYF"
    b"PLCzylKyOh7UK1N070r+TQ79lPKqyYS6G1GsRLBOdsDjgDIgKyfS2TIxyqJZ+WSJon0GWl0CG1SEHgaj2RwdePhdVkexjbxqlCvJ"
    b"MQiu8SM/E/dyUYGsvVaIO3xNEaSwoGtioInlANrKpIq47QakCQxu99GSZ2A8srWhZo2WtIN1o0iYUnYm2Bd2JAeKTVhRdNElQrOH"
    b"hvo7o1FnXFPrzoBDltnxw4njoEWKJYb8Aotr86hsHSxMbh0uoZUILK5pqiSnMs5pckS4r1p+h+oE2KJyJZJPTmRg4VSCcmnBDzR8"
    b"DOIPBB2dRsVacYLJn8f0YjqY0YOtzqhlNqXuepCQSl7WU685MNP5XCJTSSVLmSBDcPgRnaCNtFHOlHJJWD6BLWiatSWZL/0uoDzd"
    b"Rk9zVe3hdno4hg+1vlkpfhv4LabAqI1axt9yHaVi5XcE6mG1vFrExgdT48lqwkuQd3oWgNTzrlG/f9n444cfyBAwXz83ny8Ct7OL"
    b"VaLv5WAaP0xWqpkyhok5+xmi0p+5Xj93vXZuuXb6qKJqEhZtQ1ZnfrvtHWiOIc1NA7FINKBM78cH3oPpfWf7bxULsW3Z7duw+WxR"
    b"t32cLW22tSvP6H02vX1zhR/D120kahUL26Pb2uVXxfhzWz45TXF6tvfhP0gjf2+jsxCz8ZdtcHTnyGQXn9k/trGF4faJtilIyt/t"
    b"CjY7l42YAHG57tK96bpA1UsfRlBqnX67LW2UBgKbI/HRcCwc7wpvToej/L8A9T29/beedGIzCDQkDkEVQ6y6Qvg3oYcbErqoYQlU"
    b"Zrea09N9gIR2UxsU2Nae3a6fARLFlU30nbaI2rqkANVNlqIoUTGHdIyS58ZuUmdpsoKhIlPJHJqVib0w5c3FoL05x1tYXG4ce7H2"
    b"dKGxvKrHgoiIKwIM1EFhHBonvjWffE+hNTCsuwjfd+O2FcTBUpZwLJL1m581XrxA6eEqJDjJOprGq0vwE/W6Fx9T5PqTFPQaXxHu"
    b"kxaNAmPUX7uN1u/PrkM5jZ8fYZyhV5fXT5xmUwKqrXHqNqpsrq6Yj76HtmB7H8yvrZxxlC12+8pZ88ZX9dXLtQffcEMo/PxlTkZ6"
    b"gxONVyfMM6uoOMLxWWigdofCw1yDHl+QCpTa/MzaKna+8eo6NOuXGVQ5QGHy+mLRPPF1/e4XrMBAc4mfgXQctaqCLsGrxs37to6b"
    b"xhetJqB+auwvMwuo4phf4G6xwujZ47Wn58zZo42HTzkGDxS2fuUcTsHDn/kuBdVNmGNOtPvSsqjz6Uzj5Zz54KwVK9ypDVKYOiW2"
    b"h2B00bhUfJ3y4XYLxYMepo9U6kFLa2EHxNBUJlHUXMQ7o75sNOeRsjyUqCBflScLwWaRghGVADuAPjYltOo1svlSsVzlCMF44Cbo"
    b"m4sDSmT9PWQdcmhnJOopw4vAHbKz6H8Pso+uz+nwuaMSVEINZ6SvF16UsGRAfMfQzTDjr2Zh9t34SMXqONtAD1WZtwsbVYur00OQ"
    b"WPwdg4/+ZgAnfNizb6JU5OzQrkv8dncQBse7h/Iiwu4h0AjcMtZuunqPtw/aDnF8sKv3mLi0Y9IfbvCehZFwzw7JpNIkur+93TMO"
    b"zTvp4kA5QzqyLeSVIUjfFmTSBjCONC8ONteVMaQ3uW926SD2t5P2SOxjNu2VEpcP98c2C+4I+QSSfl1pWdswvqI97LImcv2G/Caj"
    b"/u0vZTGaceLdZCXD38W2coPzORDqLJWKvANzwJVE33471oPgHfDZ64CgowJsRcxrlGC3LZkulqqk34CxAaEgW3Y2E5+h6CDTSJcn"
    b"TKoJYJTQ09bpLcM8/sQ8u2yeRAoOZy1GaaNDBJhPDBJ1+kLj4Uvz1gk6Aq/gIfrjPfM4ngTm8jMk9188kGRd1aNfrj/83nz4Ve3n"
    b"U5BLBH+7+i3nNRefwCLHU+HeDfz79RM85i88Mm/9hGrAqwvmyRv1+8v12bvwCtXs8WgUr/HXXnzprMr7VloMS7mITGcCRj6TzIvB"
    b"Cb7+1TQVZlm7OUbU+7LctX4w+ZDtGRcYdifXVguntx8FFMRH2Bt7UPZzLAbJM7LjnggBbufKVv4DFn/xPYwsVxX4gUBglAImxSoV"
    b"By/e7+aKBzMeGLDBQCRf6iS16iQdpsHAFBaecD7Nd0z26g+AkrArGmXQ3v3lr+Q9MlVMi8d24/PJwmQyRx3YOZ5JTfj0nSmaOlC7"
    b"MshbZ1Dz4J1FhdJEIwZSX/DosMysj5ECyWShoGSnMoKF9KkDzWWVadi740/JsqxkNJcc27AjfG6IHPyjeZuQqonk7CqOJ4h20bW8"
    b"CCwZsqcPv1p7eWrtxSvgunmbmmdhi5/nTV/7+kRjGQ76JTjo115ea/yMMdZqc0/qd48ChVifXai/eKhuSbcWzlKzpXIZmMRS0GEf"
    b"0uKB4V24Uxn2JqWK0aP9bdNeabAk7K3ligAWToKselsMyEvikyeZlIrosFcfmddmaqc/bbxa0oUOFAGePV6/sVKbPwVMRv3YA/b0"
    b"VcR+B6MsI08K1pia5HVtphjPV4ikuLS9LrONispm+1JX/1Fvub7WKC8X4x4FVzPfEqFsa5e+Nh99Jpi01ZX6/VN4pIHY8zOIcSdg"
    b"YqvJbM4aeDYOv4ws3yyKLnY4zuajKd3/gDAI6djhjzBFDo7IejucMNnx0fV8NE8ue9P5nMNAIZDmHPphQqTZkTBrJ1SOEUdK5Y5Y"
    b"cdzTuNTN6XbYsOm8dNHD1aV55sk7PYzAyqIxrFq0KhDGEFccwnht8awJAuXSK0s2bjw65toCatEgSaMAecuysOAbdWTLQcK9/JID"
    b"mqI1xelbJOrPNH5+QmzDjPnwWe3SlxzuUr9bnCOPMXlbP++oEliQi3fWP/3GigoKcjLI+LW5s3zvqMnpj75HpofFbGofSEKwW2vn"
    b"nmFsTCkt1a9eZ1HJ4AElMw7Id2peJZduPQoRFnuoc8mRDM0UH+pcobYhHOE2ISmUEvCmCAFB1WCpQKIjzYvh+NkblTN0OECocf3c"
    b"1LConsofPtLsIEyDxFIuHnIemf8lJ4hV6Xgxr53VcP5mc9WMageHVoJzx+vfrw6YDy/VLjwzl5YwxDMHpf1+1fwKiQpM79rKCiz0"
    b"9trz+/ixY7f4UT+3ygtsbeV0feUuF0VWP1QY/eQ4qg4ST9JKQrqXHCaLN3aVnhD2bwkx0oUjUqAG8YiALhLv/z6x86M9Bwb3HEgc"
    b"+NPeQcXZwS5WMbezisaM+wd37P9oT+LA7l2OeiZxIMwH3wQUwsHDVeEYoNrVDTQFmpNKViueLXL5eFBA92SVZPeYh8U/VzQ0MUzD"
    b"4W32N5E5RB7RyaoPiopcnGJK/VLR9Y5YzTjAeUQ9RBrOIz0FI01239jeYXcZR+zhnnIDuLtWtEyDKxsXJJySxNJVWmZgWqkFS0c4"
    b"SrIWGJpmexvgrXHi1RBgWNTw/27u6Z/aOLL8nb9iTnFupY1sJEyIlwpJcYmvyneJk43jurryUVNCEqDDIKERxJzLW9gsBmzAbOKv"
    b"GDs2xh+sYwO7dmwMYflfEkYf/8W9j+5Rz0yPPrBzdU5VkEbdr3ted7/3+n1GjY43EZ7OhmibAcaq2w1QKNYQHotPUUlWeFiFGgBm"
    b"0/3Z/Lj7cBZQfZXrl6dUCrPu04p6WuVwVZZ/MloluNaz+exoIX2u9SyqmM59jN7aXceRW9ybrty/6ZxLaVXH7eI5lz7Eksd3F6mf"
    b"4qz2z/VH9udvK0DFWzx2zIJjVZcetvImJs9W9dCe0NJok8zLCYvyHvejnbBfIZmEFLED6TNKaAWV8bDn79lzAVZcXocoC8CojOMH"
    b"DUiPDNixFFsCVLOyoW9+6dP6GWoszdyXvOm8gycTBSeWRcYwy7BV54mgJbWcoJWJyK2rM3m3icG4jWc89WG9IcWwAFB62QEYP9b4"
    b"9fra1KniMwzGD4HQiHZPe2q1MrmKn2L4PxQlaUoef26CVPOYiP0ljyLvQ9ptxCaihntP1qE6WmghtCAeTOUTQ4mQFmiewzBzjEUn"
    b"dc1nSrR8i3oYneh9EdCb6M8Mc04Vb8S7pHyefCyYaqCT45P8v8icKEQz5GjCnxJz7H0Jz4Q3ZNwfpTyUwb7INvMUR+kJgkYANWAz"
    b"WKe3HzyRZYFiIuDeYRRqDZQlnxxw02ry3RgZzSQHZUqVXH9XKB6qJdv9lqSUo7CEI4fn3NBXqSGrXgS6jwlxrrS0aU89Ly7eLr24"
    b"v/f6LnKYqeeVq2vl9fnyzlpx/j5yELjZzE+XdpHh7O18V3kyp6S9RbMUVhDz6s+qoV3hUPcxHoxOWUZ85qnRV1KCAQA9feclMHvH"
    b"TQD4TTYPlNTsPmZ+3n38305idvf/+OKrT094j4M6fHVw+9IqCq6Mjkjjw+nHanEdWdEPSX06z2Wdap1Qbq49njKpOLT33f6Jh/Ny"
    b"VVYWiguP8YJ6ZR11VTde4lrN/ugRETAenEWAv+zsbT6zp27bW+6Lv5XEZEMpQXfEe+BD3VtI3s19+F04JUdngMVEtg0+HDKDJx0L"
    b"5SR/wkkJ9GE+AeRTworVGY7IqqUZ1EWamhnUgRj3FI5xlTiitI9uf2xHQvWveIakZ5Towmfca1ANL8gUPBKvEgHg2VLChxH/BMZc"
    b"auMsndhKn3JLiW5SfUlleBQiRr9ASKBdhTX2K9cDkB4nx/g+pfr98DZByzGz+PuxqGsPYPUH5SvFEcUjtRgdYiKAz9FfPRPDejwq"
    b"11JUDooC0CmhpDoIWdX9k7IwrbQncUYKrjBhvt1wEViREAOheIFkUlWPsoH+g3zDODgW7wxFXTvRc5lmqd0TXP6OUVo5X1q6KcNz"
    b"ZjoMjq8RVjn2zJhcBQq+tzVXfLpc3l3CamVLLz3xKP7tlBQULpWxBoVCl717vXvajQozKURakjjNpNiHsAW7uox2fuhobgYSlgln"
    b"BHhGUtL5033oMozNdJEmsl3BiWc0PlRSTKr/4m3G743DHbGYVCpUxyBEOtEl1fIabe2ii4Y6K+gPIxEUB2w4KycSNcQjq5oJqF5C"
    b"ATqRwRNzY/aMQKw+tYA5nEXHMqZUBKczKCyCfLZTckzh+82jjoZ4oXyqdBcqSIkf+LM/HYeqow+IgUaQrj3gEatrUynPUQk8LvpJ"
    b"WJKXp/ybW3tXrcKuXqct7AsX36aNGcq+imH/ngYie4TVBwYfHh2yzCzaPQlMgAtzYPq00ZD9bKV4+0l5+WFlZxH12WTyKC/ulNcf"
    b"FSenmK5onExMuP/5CYS/mZLkkjRn7ahLtHzBqLTmfM2wgNCHrTr1tZyzwrq5LCrnsggnpUJJRVhPhz+pJ6PnnPZ9Tlns0iUnrckZ"
    b"AAS1tP1ndOObemmvTQLy4BqAzrnPbmKI0vYOKni3F1jkLC29KC48LF14zT5E3Lg8ueNQX5Yx3+g4m2cczhRwpHUuQlK5j52JIuOH"
    b"f6pz7AlF2LImjpwdQf7t2OeN0hkid8D3E2wkk3JltHOaJZKYoRMPEWJC0ma4c4rSNQq1FaCS6dPp3nymkEnXJbiEIh9MlQkLp04y"
    b"MwLbRSvv+hX0hHmGOZT5M/pHTu6Uvt8ur6H/KHqvzj7ejw27mS1C7TC+kfhMSo/FoLgHTXQSwooaPiqpDoMrpjcONwjMFyOxH1EV"
    b"LYkmeVu6GAA9ZiOnmy1w5VCmoX7DA6zwg1uwmLC2vKpoGryzXNraLb9aJ8/k7fKLVc6VXX45VdycAlEsHjsSY5MPt7MX53+dmCs9"
    b"fcogDG7468S8a6hRi+6W7juPmMOzFfSQ+uXit4YDEXfb3Cz/Ulz4dm9nHogKPZ9DYzc9xy0IbYBc3V7FmrUzNyrTc/AQGqNEuPzQ"
    b"wzhHcPxsvpBOSZSQFkcm3Sh0GuGCkIHprxTYXWDI7Gdm+/ycmRLmgLhMVJkU12ngYuk8BsfB4Fieyb9/JLhTmVSYI9dGQ4DKdy20"
    b"Q2EgAMqUwwCTmaOQvn0Y5Jj6C69BDC7eeYiOnRdWeDkAebw0yARXnle2b5bXHlQmZoFAI+3e+Fvx5jqg0AlvByDYfusq4nj+BXBM"
    b"wK6zuHubl9yBUOg7QqHFp/vCqYiWpafQbcyq6X/ryxHjicSrI9RhrJ/vRppPpfO05U6dqVJJ3AQZZcpnsMxHj/GerhGJIu6GvvV2"
    b"OLAYTqO4F5SeoxOZYI8R2QqiWlKUHVMiuHqCZCUGDx3pehamr7T38LzV9gj2/Yhd6HqvworotywmfJJ7l96D9m8Udy9Z7kNYDmQ0"
    b"JIhBSOu4zYAwvZQkavoJywH5L4Jt8wdfp3OI5dA7IoJEb/d8N/Wuhf91CncPqr8E4tUBuKIe/fLYCSy7zhUloxhkfQQtAmOR4PRY"
    b"UV7K6jlnnPk6+J84ryzVJvRyAe2AsMtm8Jo+9UoA+oAszF9j4l78O7q7FVeXi3d24WgXl1eYsjuE3l64W7z3CrWIl1Z9m3wEq0IM"
    b"s5lc2uP+eLL7s2Nf/6f52bHjXlt306vR2HqMRCnNCZ+MZtZk/0siX7rJZXHLTfIKcotvHiwbq9oNVtkCZcU8XCRGkWqOiXhx7ScM"
    b"zbn/Y/nV8/LutNuRx17/uTz9whPVgzxw7QYu5fQWCiG/TpwXTnlU352F9+LLGfsBemSwTxNqh29PlLZnhD/PzI3y8iqnJKicn6/t"
    b"8IhKQVPoIX3MnQSo/nzOOeUYOqWX5tLUiAR+7CANGLLQaSTw2g+7hXZlOldDxkf/f2hxKC8AHuDKqQfjPVrbovdCMcbXiTGZytt5"
    b"6zo5A2UzIqvmWKRucWWfLDmmkSRxRsETeCtypuPoIHSMcBsVOlf26DPoq/A2IQbsYtF8lRCLKBrnMklt22R2LJ33Nh5PJyhhTEh8"
    b"T+TTCfV7KpNP493I1UY+iAqyw7cnCVLm0NbNITNcyGe9c4C1SOQHLXeHdC5jZVNpM5/pHyiYruxg8j0lHcGpHDhwQEzGeexqx95j"
    b"3mbog43uZI4m13XEFU9q1OeiC13uX+GL1eXJLs9F3TVhFS7fxu0FReqeQajIEB5d+GXiNvNy5uGt/KXy40348svEHbgC7G0uwO3P"
    b"KGQH08OGfWUOgJQfrxR/WIQWxe837K1HKul4RzZ89XeQOY3fDfQfFMhEJfGHIx91fgj7+aPfweg4CQM4FjpH3nhMcYJP9n6+58yT"
    b"ohvRguUiTQjdHIkKo4hJJ92U60W/hl2+hkje8U7AnN5liMH9a5LdK4mxK1SEZoQOvsr4zOPdnx81v/7C/KOM6PJ5fUlAkrbRm/F2"
    b"0VwG5IyUQetkBcbWohuZGwgF5M9IL+WkBCC3e749iEYuENS71guK2lhuTEm1o8i7EZRwQGteEYaUvBWQ5i7032f8dV24E5yFk3xs"
    b"NP5twh/zxLGvj4IwEWrVNeHyD1iExl1q5GT3OXfrcyqzpSC5vZ9v2lMzpa3HKFWRx7vxFQYvGvAbB/LALRs27N72Smnxonv7O4/x"
    b"mGWH+4cyRqvxxb/bO38rP76I/N5ozeWzZ8YxXi43DueL44kwxJcSovFIaP5Yf82hzl2xg/FY22H1NL++KwOI3jOK116UZqfhQ3Jg"
    b"dHgwncLL8437xRv3DEFJDvLcMVgWHnZTNRV+ZpFIctXenaosb6tmmWezDHVv83J5Zwdgf3L0+CcGHHt7/aK9NlecWbQXF4qz8/bi"
    b"YuXRdZA5ypcuYM64+WtIKuJtf4p/8Pm/IIGhdzOOHPqA0h92HDpsuYUboDoYdSgdjPniahyxjPL6NlIksgUBgmEUdJ3e3LSX7gmB"
    b"auZ6ZXq+vH5t7x8P7deb5Z9eART2acZkcHi7nUPv+RsvHehqpAjIQtc3jJNffWaoeeXs+ec8KntMoy/98mppYWNvcwsJ5dOnRtxA"
    b"b+/JHYAIMhc+aTMoKnieHwLNdO8HEXwmNw7nP4Cl6wCEuBeo1bc2Dm5LW4+MuMVvh5HYq8/ttVvucVCAXL9T/OHP9vYWLsWV64aI"
    b"XgLCiBeq4uVZYyibHcMtd3vViY+Dl0Xoh/8UP4IDlC8/hNVHFZ8TIrtLnudKYCi8FCz99hYPibP6bt7eumo/eMFSbPHydXv7JYaZ"
    b"y0V0ZFA4VvbPF4rPHnJYiAOhvPZXdUAUXmERWIqm5VZflhOMJfIoAYnQ0EYiPETEnOxDUcQBLrjVkLZGAhWqAQvVyLa6cQsO9YFL"
    b"zxspmf0+D4FJpRSU1QhBfdMAJgoJR9ZMZbgcrGMajsZHYBgxdyZfb1CQP2jFh6qABQ6IZnF+H4FfRwJ+SzW9LZraDy3BF1jOBe6q"
    b"wOXjsrG3zmUDAmowWFIXUfN2WHHgMWYcyCpfLPx649p4OmO+SgJNnixFrOFRVTa/9ENlYgLZtMLv93bvlK59L9J8bD5CZi+4POYU"
    b"KD86X350sbR0HR4CEa6q9VEcqON3Ctt/IGElCoW8uBeE4ER/iR1x+TRSpgTKGFIahwPdbeucSP8s8UziU2+UMPrIhf45RNf2j+na"
    b"zp1ZuvzYrdZjewY3eI86v/d/fJ4H+incAkYM/T888fWk6rd/3jFgq9YZ1r+y62B/fvTTY93mye4A9HyV7kvnCZhTZY+CpA9Zw5aV"
    b"GjyUzA61alllALEIcu3S3ju02KmBmTp3jcaIm+qwRXvdicbOJ4bckR/o8DRzEYnIxiTcjsXR4AQ6eKWmqDo6zZ6YDmlKwV1XbRTm"
    b"IZTI7upPgXOA0TlBkSRtt/hKBAKddNZagssEp/Qyuo+ewEhAJ3Myi4v2Btx4Vgy8TBqizBFpMlUB2xsQzOlkCvlEMt2bSA4qXuww"
    b"RUoggH/dzjUN6D+qDpQeMQagOfaZkNe0pP5e5+ehdCqTOKZpo7xcYF55NQ1mnUs26VDd+QR5FlrNBHGSarZ77lIj1kLMCbt48g2i"
    b"gZlS1mEJhnhAEhrGMjZrqe9ZpcuMrSYwaI/FRLr7VjiaGX8hUaPXlSq7pyWYeSb7+vUyk0vMBwwpK5qS9kcd1dfJOG7Z3w0s4wLm"
    b"5QiRWjLQKJAU0hZ5QI4wQPXJaOJ0pjBeO5wG76Oz1WPrHGyD7f1Lpa1148vxwkB2mE61/Y+Z4tR9zpBifNAWM0DCKa+fx6suX7Yv"
    b"ztsb8ORacelF5cebXpGFJ+/fLWRHRXMpN6ia4ULt8KfHUzoJFeEJVN9aZl/C0ma6dADWBKSrwVTt2c4dCUCPB2mpdGo053eT5oXx"
    b"2UNwJTR1lMjK5piRtVb0ETptI9IAwWMEOB3Sb2RyGNFbHGga0nY1osQwCCUPEXJxxyZ7EafuB5rM6TCKc9P22i1Wxzq63jAvWYTt"
    b"WfaVJ+W1B+X1h87vTqp9z2isIGGpWUYnoBOar+OMvfjInvme9TGwJhhuf3nXntk43BHjeGUl5VoDey2Xzwwl6JYodlsju6LaiZCo"
    b"X0bRSBeQlhxwYizYV9hJWzaiJbmih8u/OIWekfwpUtOv4lQb0UrS9rRirpqogNfjXnJWBHmS/ijRKr7nxG2ofEk1fVu7jscE5RmX"
    b"I5qKJorRACQ5sEqSOwd3UIJzxXeDiwQRdJOKEIQxybZRnT0wrcM1apKhf6n21yZSLnl4jYu1+NIkRT3swp8X6VzAmW8qAZOrW71E"
    b"TE05kYgdI9aV6l+h0UusMP1fu8/9US91/a7rLqG+Z5NL95st2z6WrOnlCgwiU4nE+w0IVFyJixaVMhqGPBTkdALT7OXzQcTim8Rw"
    b"IU3EgshmE5QCE7bNF++K8gg6hjLDxIRNj/bigqpBaZT48vwCPYr3R4X3QYnV7Q0DAQlDQ89Yso2jU4PHQQMVcVzKgFpcXuH8lZUn"
    b"c+XdafSUvDdtT180BsaScQN4emXiFiWKWUoPJ8cM9AG8dA8tOCvPhUZqcoc5P1bsWVzcfyEJ2lGmKHBPsVzOA1S109JJ9EcNdzrv"
    b"elygiZF9m9KDbKVxYJI7H3nh/NS9oVDtUhr1UKTAModGTxcyppOYrW4/94se0ipodP9YNWF1nQ3QzjSoiTnX2Ggyn2b8fYpacsvs"
    b"ws+2LdYYLFnFt71+89ruNjqZIkViQv3lUshdiNDv5NIz+hKZ00AqRrreJRGlS+jB5Q7nESKNboh6m8vMYCPMqt2XAVm+N2QVKE4L"
    b"SygiBMLtwXhNGLIt1UECgB8aMZSQ8Nkpk1zyOgys/g2f2tA9Gms1HP3ki08xL5t59PjXWLMhUh9nDZ0DGWrB5Dk36iLPUZpTfdw1"
    b"RycCFfzNkXOcWgAxNzlpPseHn04nsUoo3ciJqNdmPqwEN0mNhH5BAdVKSTrIwZlmzxf4YJJSp0ZzIRsoaaepXzCy1E0vFSzQu5XH"
    b"HRE7nV8mEEjNAq41t8hgehy93oiBy88NyJbK68petfeDwHgqncyP5woCmYh5SlcmYTRWhjh4pGqeLj8nZ98K6eRwCzUvqHIpLazb"
    b"9yeLSy9Kd585/vrAsTF17F+30Da/uMDKUy1coDyCDmN0ejAl/kNMf2OjHSj4hlZpth+F/5so/f0qsYb20X5YbV2+KvmpC0vRlkaY"
    b"YnVdard3GF/Qwh0O7t940ex6HFAlAm+L59WkCYJM4ao1Niu+qtAqN0uTAs6jPIB7m1f3dr4rPV7H1IgPHsPpZK9sOKnwVShK5+zp"
    b"K/bGX+zdKT7AQS8VJh2FaxlZo169KoWrOsvBUFXdTkzQ+Mhof9/4PQxK0d34pzH0WIOZHDzI96cNWC2smIMUAbP+jKXpLa3M/6S9"
    b"K+gMG9knEllI6jIkVQWeaaJdlaBiNbc8DC9ddJG8h4nuRgJZF86IgGKkfEc7ZVTuDfUVxnMhqSOln091drT3EOp6Q+jj5P21PfaH"
    b"jp5IY6jrha0OEzcSfVi9RrzKW2F878Dt9WJ5Z7V4bxlubBSO9wRLbMqrLvrXTW9Rhs0nmIj47nNojO588/c50Si0dxo7vKH47TPo"
    b"haUzqJe9sgEdRe3U2Wm9qDKEwZdcew8lSrM3eyY8lB7K5sfHMulvBMqjEplRIxYchTuURd1MjG/NVCn8iJOuy8TuMk9COmuiYW8w"
    b"TE6NPMYp7N5JQN7D3r5qmUGLNJwVagoC+duLJTWkVUbW2xAUmhNFadyehpSocMkNpvcqWoFWSFSGRafagqueHgxZ/ZSIt18xNgv2"
    b"0WkweDlqy/50VTCCt4pPT0tNPbK3lmOdOf7XsEADdIxWLdKH+ijTvAlPw5HI25x8y/8C81A0pQ=="
)
_EMBED['xy'] = ('新云帧享.py',
    b"eNrNfW131MaS8Pf5FVrlwo7CMJ6xjeN4r3OPA07CDQEecHh278SZI8/Itux5y0hj7BCfY0gAGzCYhJeAnQDhLSG8XggYG8M5u/9k"
    b"Y2nGn/IXtqq6JbU0GnvIzd3n4YCm1equ7q6uqq6qrm7ekLa+uVXKFLN6YahLqpiDWzsxJ/KG1P1H/gF49oWHq0tnrcXbq0s///Zi"
    b"esSIm+WhwWw8U/jtxcx/PpP6DrxbHJdapD0fWiuParePRd8rFoY+0hVp74Q5XCxI1Z8v2UtzkTcAVPXco1+nTogAs+W2+Ijx69RJ"
    b"6/QV++qz2qvD1dvLtalT9nc3f3txyj590zpz/depw9aZI/b5h5g4cdV6cAwStfsvrRvH1755aR39ce3LH1cXp+Cv9eC5tXTutxeX"
    b"oS1JWrt1Ye3aL5B4v7dPkloyamZYa8kMq4WClmthH6HtYoEKW9PHqo+WA4U/H1aLJV0ttBxa++Hs2uFvJlsOQSHr+5OQsBYeWqeW"
    b"MPH8yeryCiTs019bS2cgAYCrVw9PesD5H+vhWeurVwyUdePy6uIN+/4v0NtmoLNhOj/rtGXPLVSf/OAOZCzTopb0FkNTy5lhAHf0"
    b"8dq5+7UHs4GqThftb0/bF44D6q3Z84i8ZKdkf3eNANce3LK/PBrA0Jie1YpGyyE929KSTCQSk5hkIP8yppUNvVjo3jygFvNApt2b"
    b"OfK7B7XCOKB1iHX463v2uZfBDhPgllJOnaiUc38x9Gz35hEd/+0sZLXx7s1m9+aJ7s26MaLjJ7WQLRf17M5st4hv/LM5X8xqud1q"
    b"XuveXNAO7tDG9Iy2HfKgW92bG3dRhDOsqVmtLI1VRqVuKZ/dFoXuSFukf+38V3ge+PjD9Ie9/6EQgTPyhCm1vpkFSlxd+cb+9oHU"
    b"07t/a+u2jq3vb/9Igs+E4Ol3VUPraJf++9jXkjUzKyVbJevexdqJI9LOA0De9sLPUrLDyTLVIZgSt0uri/fWLj4ByA6wmV+njiDw"
    b"6uWvgE3s2ftAV9bDR07b2/v2QZdq96/BR+u7izCInQe++CIxnmB/WqXaL8/Wpubw05ak2JB15k7t9nVoZXVx1r56be3OKewKNLa6"
    b"OANkAR/Wvr4JNSFde3AeikJlrHB8CdgL+l69ewv7cEiypy9IKcmafWydXYHeAwSvjeuP146fqp28af/9mr0wI5UmMuWJklnMFvPA"
    b"rZQcKqul4QmEffyOdeJHa/772tyKNf3QOna0unK/uvTAETUc0QQeGnBlBIweR/D4R+vYKfvkK0hD7er8E/jkdCUZl/bu2d/n0l+W"
    b"CKVFN4BoJJqlrGqq8QEQdBWY/RbJR0wwn9aro2vXlgkITAjBbA3AHNJMNUvctkVSs1k1CzzwXxfb4M0EkTmiD1WAJ4bU4n9dbIU5"
    b"sp6/ss6eAHSunTvMRNT97+1fTrJRICrPPLDOXGCjQIal4tI2oI47tQfP7EdHYPashR9B/FaPPK8uXLFPfo2sdvGpPTNbu3az9uws"
    b"SMzayn2GgT921dDzpWLZlAaIxp23YdUYzukDzitJLJ4uGk6qrDkpw8g5SXO4DCwI/Olm6Hm3HMgHgBrXyuViOZBXUstGsFxZ+6yi"
    b"GWYkYpYnuiJIgYPlYp66GjdKOjI6r7CfvamGhLzK3iLaeEYrmVIv/YDoYCAyOdUQi0WLAyNaxlTYV/xTggLBNrcTdce366Vhr1Wg"
    b"YWwyzT7CW4MmvQJAK7uLBS0IXeSd+LD6eV4146WyntdNfUwz4hlq1XCa5Z2glgfZS8OG+Xe33Q+QyLsledg0S0ZXS4ugIsiRd/f1"
    b"7N6BX8VlX47s/fB9zMwU8/EBVZ+oFEjgx9VSSY4c6N2H39ri7fGEHNn+Qc/u3b27MMdZN+TIR3t2sKx9WjavQz9MDUQoVGXSGL9U"
    b"9JFKh6nmRou50tuduVzurQMfvDVR2TGuD79VGRlmZT/auWPHrl4s3ilHIjt6+nqwOqI0RYOV/7q3b9vgSMnMJj7Tk31/+9t4ZVtb"
    b"puetf9/Z2jf2fwC0HGPlPhsrJCtvvbd9sNJZUYtvF/XOhN5ZOfDBgf2d1KJTrnOjbsUi/ZHIxz3YpeIoYrSlPZ5sRUS827O/N/1B"
    b"b8+O3n3YwUPyx4ZW3tozpBVMuUv6uCcmyT0ZnCp4kwGROT2j4rS1IKfFJFMbN3FB1SH9Zsub8mTkr/v37BYBsh4GobLc14HMq2wv"
    b"FkyAsrVvoqSFVfw3CRZbYFCzm9RXqDYZ2bur5z/WG+MkAH5DWn1137oxi8vs6WX79Iy0TxvUyloZJBmTdtaN22vHz1RnjoPiiYod"
    b"JGa+rd6/BuJQehcVUmv+pbV0Iqon4sNZIzcQBzJU2MJHn+1TLkypemnFmptFdejbv1fnL3Jhu3hrdfGEU6ZLCqH8FmkV19yf7Jkp"
    b"WNZYL2qvzsHiJbUn2mhFsS9etR+fZ/oPk8L+8UjW3GkYZL6t0tnC1toWBsf67rjUmkhAR3DFS7Z2SmyZtl5exGVxbhrASn37JfuX"
    b"wwg30rfzo949HyOPvh3Z2/N+b3r/zr8h0bcmkXk/6k339SEzvZ2I7Nq5v4+/JVsTkR29fT07d/GMtkQC5sf5ug3eoMewhlSXbjPt"
    b"GVbBtWtP7atnpA5chaB7a9eWQE2FxYrNC9NzWSYuktt39ezfTwIsFZWtmdtr88dkoGKeUmJSVK6e+wXMCszlKZa7/KI2s0S5LKXE"
    b"IoLSB8BO/Gi/+JmAsRRVYwo45bIUA7Z0x1o5D2gleO6LAnz43s5dfb370vt6/q/HH7x3Xfyd8jI5Aymcaeex6vQj0JRj1pkbtetH"
    b"Y/b0t6tLMzHrwgLUjFn3n1pL92LVEw+qK3di9r1bqy+vxqxjX69d+ikGXV1dWYjZh+fsqQsx+8jd6oWzMevmcev5cgzqEszTx6wz"
    b"f49Zc6fsqdux6pV70NOYdfTp6vIF2UOBXNaGgMuELiFHXDoWW7t1yV58AD17aD9/GbMv3rQX7sbWrvxkza/Eqi9P44/9+CH+1MOc"
    b"ABNCgNiaaO3AxzZ8tOOjDR+t+EjiIwGP5Nv46MTHW/jAGsltW+GBRZIJSCUSMXv+iX3xJ97WJJcefLrXQbODUYa16u2ziCcH9wzN"
    b"oTjk+OVTANWr55Zj9pcn7COX3cli+OXzUj38cu3yy9+NZgexPmxbsw+tpVsOtmsnHzHcn//fxv3bCbIwr8c6nUT4bDA2W4/oF66s"
    b"Li1Vb0/BCB+vPp+L1b56BMY7ZPxBhPnPxAo+sEYSaySxBiApFBFcnGzM/Q5rMyLl1OkQIhcCX96rXZsKcL/D6IwCOQFz6qy9moNS"
    b"jhBwaJUIuBkkc7T+/4VPJojXJayTnEerp3+Cv9bRZ4Cdu1DLvncKv1aXv8Vh2U9/rF65WXtwLGbduwUMVXtwLwZvYIbaJ18ATQLy"
    b"V1afX7W/BDKbX4EyMevwZXvmpPXsJp8C+/xZ+8yTWPXcFfvJMiDLWlyM2XPfV++eJSTPwBwdvbu6+P8I10mHQRM8EWRRd+VaB5lg"
    b"QVe/eordWrt+JVa98RKUlBjwrX3huLu2HJtfXTqJFGufmIrVnvxQXT4Ts0//QJJw5Y59bTpW/fl7/GZfPGovLjaFjV+eWTf+wfEH"
    b"yWcyEtm/Z18f1x7shSkwMHAF5yla2iENTMZzMUW5tQdfgcKCuTyFS30kqw1K6SIZOkYUVVpuvZU1s1IuSKlDMg5sHGqN4e+kNFgs"
    b"S+OSXpAMs0wVJMiQZQXMyJxuRuWYrEj6oDTuAh/UcyaYXFEOuFgxUauYZCYb1DX1bExKI0SuGHnmY1k9CGU9dSQ+pJlRKK9gmxwE"
    b"h5mC7H7XgHH+HJJHtQlEONIDjKGg5kkpZx5HzBlTcxXMcnEAbVIzVEVRJmPhAPmcCzCZ83J9mLxWY7BEICJQcoSuD5TqNAZpgKEr"
    b"gmROVBEkn2SVT/IAm2R4HcBZIXLrF6D3iwQCqIeJTrM5Avx70x2JbOBgkep9WOhROrpgLZ0HPXnduoy0jIHieBqsJIe2SkgAiX7p"
    b"TQlgUU6uLmcc1XiX+HQcYRmMay3aum2b6LlI6UhO425GLjWOGbqbMS592i1Fx6U//1lKKtKnUjQxnky+S7QvbZYS450JScsZmpRQ"
    b"hCqbu+HLe+9RDnS+rnd1feoQ+qQXxqBCKYVdlbZCj/R+RdoEdbf1Y7M6by/iVkAklYtmdCwmFQQ4wvRFo2M4gIIifSFB8p13pGgn"
    b"gC4oikKDgK661aC/DClR7MinBBlSMTZ8963V99bme2vHt8R4R5sLXegLwEdS2v/unn9HQvIm15EkQ/lKLopk6cgoKJag1MFhPadJ"
    b"AwKqBoF4N0vJwKBxylQ3S8WxRFXfDNIEqoEJ9PWWUAGYcsiI977s9FIbL6mFbBq4Lwr/eFcLozAF2N9OQFc767M7+dFkBz7h+xbo"
    b"iBJGCG2twvwdZNMA0DEhIjIDrIRQxxPJGGQnWunZTs9OfCYT+GylZzs9O+mZfBefbR347NiOzx1Uvofy23f0h3UKB9Uu9tzrIsr4"
    b"1MFUVAdiAty+CeW2SCP9BGHEg9Cu9ItTpgM1F0aB8aWEf+IIHFFGykwl+/uRpmCsKV1qacEa0Eg/LCK8QGu/8NImviT6+70GtZyv"
    b"yfZ1mkyIQJL967Tlga8bqh8+TKKHlm6J46owKiDrU8lMjfik7UGXyArk6EwP5IqZ0ehB4AlM8CYMgJfTDTPKMsOmLinKFQPJ6NNu"
    b"oiu3cLmQFYoD1YrS0fCQM94vqAT9PgKgPhiK0A7OkpHaRs+36Zlsw9GblGdSnol59NMv1Gyl0h2sToL9tLOq9GriK/600rNDrNtG"
    b"xd9ilVgXktt4XdYua/AtBifpo0nEw78ArwfIA8ecaTy7JF6As1TAnApcqLZBc0Yqg5PbleFT3N5fV4cXwc5xcZfgEpW/JrlIVVvx"
    b"0dYIAPIjAlETvqoipFYH0npAWl0gatJXVYTUhpDWAdLmHw5rNekMwgPS6gHBjQmohMh/U0p2+JiqERn7SZkgbJF0H/8YDv+UKmUt"
    b"nQENFoRoTNLHwFqjrS4ODmVzQJCnutpa+xVBhR2YMEHxKqsT0RwsUlSZfQaw6GV0Oak4OOj1GMbvFgemEvufGfBBxU6lupLQKAwD"
    b"s41oCmU1+9uvCPVSSZqnKLYMS3hre92ChWXaxDLQcliZdrFMZ2gR4hwsEfxGw6a6uBjwz+yPx4xmWVPzhN2gBMsMeEPCVSyvF2B+"
    b"BXSBeARUKo1oIajhoFGAqEcaAHAIwnv/lPck5acPhmao6ekcmTxo3NAFIIE01IlJJXUiV1SzvDVZlnEP2t2AZi5p1GPP3AFLW6Jd"
    b"6FO+nWTQbSnrtPTX/VJ1Zho3oWnHG3cmjz/5deoIACXgOul7rD0iBa43ZieE/GRrF8vHESIFwedU19ZkBymFiD3MUSScc6bQ4DvV"
    b"gDExPQJHFocZKWa1qMz2JRQi+AiXgsK+m25IhaJJm2CCpcbw5xWLF7SDjLmEPNy/SgNGQBcqFjJatw4qoV7QTV3NpckY6W5V4pww"
    b"2Jx77Tvbb6HN/46tPzU3VCzr5nDeiEkYLWF4hOzs87mNRr3CcRgH6XW8VhyGA6yKLCp/Mp5ICP9aZcUjVhgVsg2Bc4ZYLEeVIAbh"
    b"U7xSgrFrnOi3UNagXlBz+ucar+CgOyjGuBBziHegoz3NSFqw7HHtLmtxozIQLcupT3u2/k3d+nli69tbWvrRKIR/Acte4dW2dEty"
    b"t4z6XrQdzQ+gLAPtj3b2oFLuZqzIVLQfHofOZDWiMK4ShG+0ihWBDdhIoCIJC+wVGr4xJFqjG4nA40MWxSPh/p7kBFbhztNvL+ZZ"
    b"yIh9aoZtKNmProrxGwLH0bC7CQPofMD1H388mmMcRP4Os6yXoi6FYgGsXTcKh5cH6TNq/CCyZLC560rid5GTg/PnwPEk4p+l9kSj"
    b"BlE8IoNDa0geBs6mu9UrqurilJHpi3uatGILso9TVpxPIRcSQC/6UKFY1mT/+o+xQyiiEFI8xzEFEsyv8MBQqCD2UE4hsENyiB7F"
    b"h0XAPH5qSDzEwsWCqRcqWsSPFs4WIxQhIfKEMO0+l1aTU0wBAY3IHzd94yipxVls3H0KmWASA1GYV8epWrwMIiAblfvRmSdmTDoM"
    b"Ch3EKu+ItlPd3Ib3KdWFNVFlVJpEsNtLEQMbO3xWzlaXF6xHR2B9tC9eXX35Xe2XC7AWVuef1F59v6HPJ71//y5YPtA7YBi5eAYW"
    b"cFNLw5SqlZyZxjlH8aC45eKZYS0zmh4uGiY6v9CVqAL3et/HtLI+OJFGQc5hbu/d15fevWd3byS9Z2/vbnJp+UNo4gMVPZclvoCF"
    b"gXAQKLC3XByf+ABUxxwUODTJN2kDhT7o69u73ynEu97tdAyquDIcN9mjUDnGA/KY1IvRIs6TGBcEOks33/D2JCLfeY9WTzy1pw5X"
    b"rx6OSSgGF+4qIPLsC/dgPlpqT4/aF5+ignJi3npxxFpcxAlxKlSXL0kJQT4KOkZQXyAD3tALhqnC2k5KR0yKkviKeWqtoqA0pXmQ"
    b"YPRMmfFrJYCieqzvY78ME9iLbnzAIqyZw8Vst4whZzJ2gXrIhPT7vX1cLg1ncT3P6hkzKsaTuIyDlTwCh9LOGiwGi7il+USEVjiE"
    b"MgQMcZIlYwqTwjFpDIUcrxfXTS1vRJVJzzJ3SwAg/lWUI5/F1Ww2zapHsWzoYmug+5OTbZzkNtT0qIP/KhsKB4SEnmWaXZA29I6h"
    b"aNFmxD9pKrk6yAAikysajgLDpYsYxUYs0YspjMeCrI3FGBSKY39ilGq6i+uLtjrYnPQ3VFcSMWGNAeaIGtqQfzdFDNCLf1YpAr0g"
    b"mWA50LrUQa0bVh0OIaOa6ZJqDkfNiZKWBvMoZ+BU4P5BTEKXP9QAPRbtkSFHCQJAqN1FU43r8K0nWUx5cMhkoMroEXO2KX3oIdZK"
    b"NdOpfp+uKgejy2VYcOQWOT5SBEOP4Yuxi0GuJBgKKr8yRVU7aB0u5jWGFT9i5UCcO8ImkDKLeJfrQbHYcAZs9KAPjS5Qfxi5C3T0"
    b"IIFr2ZRlEEH9xdqurmqqeo4BHtOz4R3lEeSbsi2bDH/c+CbDDcuGpBOYvcnAVqLCVoBJwNH/iRHoIBNoGw27d6B3n8KTez98H5I8"
    b"lrCJHRk3driJzRcMCa/fMOThrnEKGOfqlBJcKpT4sDae1YdQoGOvdvQeoLA3tAW1rNzF1gcg0UoBvQO+rAHcw0LyreiYjUyXzTh5"
    b"haw25qQxdC4RT0wi9PSuPds/RIefE1Ib37cL3Q4Kfdy5+71dO9//ACPFUrii9rsziZHOaWazaFoWuZMN9g2JhXaBRfHr1CmGtV+n"
    b"Zq0zZ+1zL62js7Unz9d++M5auoXRevNL1v3L9qnj1aXnYOHbF2/VfviZVa/df2hPz9Wccx0YvH74a7Zo82aSibZEBzbx4Nnq4sna"
    b"yop973p1ZtqevlC7fQRjBCj+GZrGcyMPF2uvFgKR3mj8zF+1792ovbq0dvwUmkD3Z2rXj65dPmMvLOGm//QcxgCy5ljwtNs/MXja"
    b"nv2BjpvcAd2tdvswquMTaRBojjdjdvXFZdDpaieOWNNPrelnDlKORLydXHmT8YXzl+gZsUrKNqkNuRzMG5AsW7Pi+MD1p2jEK2XQ"
    b"FYr5aCdRTlTxW8FIa9AAGhgdwtyl0fAMCAohRIBzGVAJNSmX1MwocPFutk3K8jhTwjswFbxzdoR3zlPC3j6jR6CnFCX7kTDdUHnn"
    b"C5AqfvCF0TvfiHj7BYgDzpcBquQe9wgAc896QD5FCPNgAY4JFM+GCYoDyNaM1k185Lg5dXNYctjDt3mGpg6VJyXN6QS9CHMjbWWf"
    b"TPj0Z6mtI5EIXUr7ytwSE4C7A/DXcLNRXRPYT/AMM+8XWTDZSr5kRA/5IITOY3CuX2NehblNhCIbiNfYk8uCEKYi/opNU4AshIlM"
    b"gj5TMNC1oxoZXe/mos/QQHFQzSKYABhmAUC6HNuPKSrcimUmA4Wnb/EWMfFoh8zNB6ajB80H5uMeGEFQ3FT2+V9IpCuiOYCB/ywk"
    b"Q2EhCZgvi1EafNbpNAmVGJCVOgWKWWfrEKZLh8xU90FT/KWIBbnbl5XBHOpSwl+SsV0dSP8EKdwl4K9qUj2BIfyf+XKGZVwWEFmC"
    b"8Sdb49Kou7qGm3gKBpYQ4XgLhmELJ1xcCc3Otoi+Y4HPBkQ2q0M2lGQocxbb1+LzII/7dPVwUnRPBDl0KDCzJ7cbEXws4CAKJV/H"
    b"sFIzJnMvGcNFJHs5k9NpjJQEeyQb9Dhx+eL1o+4r8HCxMPT5cKVIUwtN+IqEj9k5+RQyZMaFzQ12wwGT8oy7TMnwcR0KW6carSxN"
    b"LVM+eRdYsnKaPs7kbjJECm8gdV2gQWltDOsjOrwZk00g3n/I7J+J/iATdfsXviCjbGhPMg5lQoKvB0yIR1kj3QgqJv2Dy7orpP6R"
    b"hb44GhwtmokhZQLKCD0VsYdQCttmI6SkK8U81AYiNVylvo9SUVMtD+H5GkewosNIy4NthT1Er65aNut3XoqjTdhHt6/b389tbBwN"
    b"6uOoG6O3Sth1wQUGctbxLhvr7B4YrOMGzm6UTp11tbSErKLugTS0V43UW139jSEY4SCM8BphRTm7GWG77JmcphaYzkC7e35nu7sH"
    b"9efUp+/0b3lH2Hyi0tg+T4RsvygiKOYP18AkAeaQNxcGjNK/IThJ9rsgJO5toPIsXlXx5oF1mhSeNDrhoviIYRBdGt0dnvXHJ0tw"
    b"dvKSuu/wY3BzACx0TgRYnGkZ5AfYyRUTL9tRVYJkwt3YAmIDoEgzDQAruHmOAsMHgB2CXEximcY9rzeexorZNK0j6HbwZ/M4U/wJ"
    b"fCnpaKg7vOF1cFArDOVhbTQrwa5n1WH45uTL4oEngljW8mp5FEO9Q1EC6xesMSWQN0HAhlbW1dwOzcgEvzggQ1okpxcfXmh7WCBs"
    b"BuigLMt0qCk4Eh4Z7qcOFtkbPnQVRF1dBSe+uEGVDKxvdXVYbqDHE2phApbMRpCMDHpUg5BYbkiV9ECuUh5ohDVQzcrmu1Qi0IsB"
    b"L9MFOOnjUwoxU8vlMDaFRRrXdY1CIjHqSzP90lZgYAKBwOr5FyOc3XAT6BoqWKronQaEUDhGA7mhBBdgLA+w4Cfl8FE/c3lq621j"
    b"MgevVsC9gKivsiIGwuNhYq1AJZT6QG3EHNvAgu9R5qrkvsPBAXE/fRCDkeDhmXD1sodVD5U+4idP/gwO8MKOmKDcqGytPMITHLCO"
    b"oE+TdRv9S6SHe4Aw6+NybhdMU912U8NyfFq535qthVrJALO3aKo5ThoJb4bB9i7hbGiFSl4r45YOghPIQsNtFizja18rcfnPGhIO"
    b"JxTyfqxppRCx7K1ef+ILl5fzhriUCXRUyPuphRoijqQALF/xfFw3svoQLnghleTq3bubDDzfidGweWGohkNO8ibjT+i3yzquu0Ke"
    b"042O6zbtPvOBgW5Om3zeei1+EQx1NgNbnEBqlHaOGS7MpicERfLxiUaqjgIxpLooEkUAJD99AIBZG9O3T4R72aDB9PmEvvjRvxw4"
    b"jXuriL/7KIYbty9Iad8ovGzZVXZoAWsMyrfC+QYTWBTFhoLLIotEQ/ncuCFBfPuaCch7p5m0X9xHHAmoFSjcktraAtLikwJKigZt"
    b"ZsEqV0g41OW6umPEk9phKg1poCCHfqdeI7Yb1Gx8ffLpNiKuEd4G6gekwxUI2oQL1RTwJ/Alp5I1LvoefYoC/Qa+ZfWyxj/X1RPV"
    b"At+Me4qBOM6G+gJ+5DOPSgNLNVT9HIKnpWRTVuJyjEkX3M+kBJt8+/IR++JVKGGff1jXJG1pYCghAKULPMK+wxTj0N/gpgSISFcx"
    b"EVZbKB6jJYyvM47SooNBChAM9Jh67j5+4ZPEtn5om+ass31zmV2AY924DF3GWxDuzVUvf4VbyaCESHjRUKGSy2HMxsIVvBhs4Ufm"
    b"84QCfm9gnZM2wxybpAkxn5Gw/otnAPub9PXWfSprRiVn+hzBLHYaQEacA0qlijHssw9Fc5kZgCGWkG8XznGCrr64XF2+ZM1eXV2Z"
    b"taZeSK6VLLXwi4UAgVJHRxwvl0BPKt1eZJ+6Zp+eCa6uYJ7mVTMzDAbqp2Qq/wUApdxoSYyVpL3v+M7Qk1UiOCOeKx7UylGlgf1N"
    b"bg55zLtEg/dQJq3w90P/I4A75AHzVhde7egGhhLhK3DZ73EnGvVszg30bVS/KnXaNemCSCIVHjmSC4EElBEGCF0MZOWX5VTsE6N/"
    b"C0walFcaQxeDJrH/qHoRtnCDkKmVohOEqroDxrBghe+k0uxKqy++tY5OI6Vdf8xuPLEu/WgdfWHdf25P3bbnn1g3V357Mc/vb2F3"
    b"tizNMV63ztzBm8EQEG6wvvquev4SOxzpO6Bb8YaLvAXIqWxAbv2wen4iYiAEBs76hnCaCPh78Y1179sNovq292z/oJedCWbp+t16"
    b"vlnPY2syHNkgW82c6PMUqgtuT7TZuvk3d56C7I6lQjcvXSeIE8Tr84piNQzpfQe74q/PGywVS6yvJFw3bIHnEdyke4Y6YzgjJoGI"
    b"4c9aqd7nGzp+lpmC2nS2w7e1zsRuEBcInMQGBhqz6nh8oD3o9SVmITECCp2W5UUpNrs7p+YHsqo03uW0P94PeFJSXSLMlhaptb8+"
    b"4FfEnIg3Z23FTgNm2PVj/Oox7xYyjhDEG0w26t9RQ8sN1q9rtMR765BuHEAb9r1iGeQ+VYlJnv/Wd061mIuiaKGwIJAtn8SjKCO+"
    b"yJfalegnf/niTwr3Y3rOXr5SKF5zebVQUXPU5HYMU23QSb4JIIxoh4ZCV0PZF15FXFzRu8/HApoy1PPcI8yfkBuMsw9o1LIE9dhf"
    b"JD2olw0zrZXSB9VyXiM/JnlTuLTbus4fyTpzwf7lcOMybmeZglV0RubYl9nxmDQCVuZYZVToOmg27CY/a36+uvwVuyv1txfTXJae"
    b"uVO7fwMvoFi8Z1+Zw/ualr9COUw3MVqzj52jAXiJpBMmi4pZTAJtorr8nXX6ijV/NYYKljV3iykP9slb9vQdRVCrmImSHyjSgcgo"
    b"O5uVxOsWWr0k/npJ/Cuces0bQ7AmZdkxKDTFgXS8rVn3joSYhOc76N5PZDjWpp9zPqPQP7nxVaKbDLxMlJ7sOtFN2c0mPibwwS8V"
    b"3ZSVQ/a8ZOGuUQDg3S4KL/77RTF8DR9eOFs4vPAYN8UX5OY62NzQthEdZRQ8/wUxxXR6oA+FU4mIpvqtO4Lgbm86IXIUxOG8CBuc"
    b"vqwBfA8H2Djazu/JaxSg8ZnhRXYfkoHG0aleGZ2MNd5obD4+IyDYoVK9tK1zMvJodSQnv70SBIkfGh7XYMxUT86CKQEwG4SLuIHV"
    b"esE5l+EWBo7hxrSraJq6MayH75iIp8sLpgcl40Z1JBSMdaVAOwLAeJ3UY2y+foCu2XHihL1wl8W5Ve9ftKfnMFDPCeZjMXnMwnAD"
    b"9eyZWTBQHNNu2p4+u7p8143Yk/bv+FDCe14ffon3xNW3K4q6tS9XMOLu2we1V5dWF+9Ul7+xv19gZyns0zdrzx5bx5fIKjyMd+u1"
    b"Sfbda3jz3vlpFkfSaNrQG0pYR1TwKMVbh6GCGG8IXSd8QS9hfn37vk6IPIJAFYISjokpG5VMRjPoKpbiKF1Fc/oZLg/Tc9aJK2Fn"
    b"f2Cy8RAMPKE/CCsS0l+fDBUMS26uhywmQkvsDCQo912+yERfaS/QXyf+9RRQdjOgT4OCMqGKJOTHxIWVXaycdgJlKZqXXazMr+cU"
    b"bln2o0MAQjEuJiiLJbNR4AfeZ8FKhJGyS8GNglKFuabbG50wUPvCQx61eubZ2vHZ6qVlqGgdm609OF/XTIOAhGYC/+Ry0VTN4Pmy"
    b"kIAwWW5cwgkGSzQu4kaBrQdHCOiqF2qNw0Dqy3J57I/qoOiEDVhAZjjn1yHfeFR7QjfG05Wa7r3IcvMyPiYdHJ7wKSBM3/M0sXod"
    b"rLllQLBZsEAKL2mgEdaV5CcasRSdUg4nEBceBvd0qTm804gAJ7vaG4IW1iLqQGByGWoBA4haeIn4eYPT/WX33miQoeyqaSYGHVE9"
    b"vbp4HDVMJySc5YOxX7t2yg2PhvTq4kmmsgITsXmsY1RnHlB0Onxdfx0KzZ4XNlj/zZnZVrRD9Fzu987uujP8erPc/Ez/7tluYsZ9"
    b"s94aNu3QR5m5YUgFgM/1vRwoa+pofaROzOVSxodscWNcKnvrEtlQzKJaf2mi6O1KIbhlV3cayjXT3BUvfPXa+OyT72jnerFV0K0G"
    b"UVVNWYRH8X+4aMIixPM+/EJljip2vZjP6EUfM0U2sj06us+M9kpoN4eul/PtneDPpHf1HO1re7fP9U+Kizlrru4wG7SYkvlNZyTi"
    b"+QVokfqjdFA04hsPM/mFQQmDEfULGQsDTTlXFTerZEQ2tjmEY1TrmBkkM4wmrYzwYAsfKZOz1BerodT7k3BbDiajUXRHyPqIYWIb"
    b"h1KsuxI2E1rRKMTCd3+VcPyVkFfn43aGSTfrsTIh4gW3O4PwGoUXeGGpZk7jtpKz04xZzMjhOfniaEXVKQi3LqJdmCpCdbgutMGN"
    b"jYGJMZm7gjrSWNgLLUKF+g7xM8c+WzGAHfFbWMRHnb+froPpYnekcNTBeHFt/vqeNf+S+xbYGeP6SB5B6GBbIFTwtpmujoRfejiS"
    b"gsoEHJ1shXOYnJUUrwup0ww3ki0ZUJOHiuUJv7ykuSoNOYLTcQP6/o+GIY1fNJCMkZGMJFRiC1nSu9gzLivowaVdIa+Aa27LCWeH"
    b"XQg94UdJ2cUKeraRge4eOuWGYiqDPnX3ii1HMgeWQQ7buZpcON5r+pyZArNkcs7GIkaAetd8MsOfnYd1uydmCsjHcJIgEF/cXVNw"
    b"hGAXF4oQ09IUDHS7B2HQbZ+suHMlbBi6qaprlnsXxjpXwwZu1WINORCDtjOSd5dwtA/+dm3Kkhnd1OHlxua1czH/H7j2vd656nWW"
    b"R7bb2czamDNMN0DQW9KofYHjQdVHbDYMTHRCdSHHM/8rOQxhQ6U6h0Xe6Zbc/+nAx+CZYqXAOjFEgdWsNWLXKOVtkZKk7yBAyvbP"
    b"jCDw8AMIPPyhU5McOM+iNJ78wHuXIM/pWthJCplCI/DUXKBL1KM3vaHEJEfMAiifhIX3MLFKxBOUqQ3kJtvG8UtNqv9ZRc+MOofv"
    b"SkPdKAwFv9FBznrIBA3k2kaiNdXVVidQebYXr1cnVJ1duoOhXOBOUDIwO0lhVvAko4t8D7spYfnKcOZm6OnyWNo9LB/KthlC3duJ"
    b"P5BjQ0/q/9MY83fQ/OuSu1vodck68zp0zQKw/HStZw2BhNmBBPccxic7hCMYUShKd1X59CzIjElR7DTgv1LKaQqLL4F8ZzPGUHzX"
    b"hvmPGzSg2BDy49THBtHFQ4MbLxTef9nSFOF5TUIJvN11sgk6DF7ssA4JsqJNUmF9NLoTl800fi73Xy/cut4JnKFbjrql9kR7w02b"
    b"0KnY6LsQ65Z2gqpDY8y9IQtSOupWV4J+nfWUYJ359wOWFfpU2L1jE/XEy3PXM6SYe0zwz5AjJeFEOFNeoyDnwMc6/vRwByMG9Pn2"
    b"KbRywM2RU4eQXRFvpffgxXfZnXejAoV7N9Sr84y93Ti26CfZLconX3g/byoYbo53J4iIDQTCiM4kXM3iQ+VipRTFDW1c0pz3VgXv"
    b"ROQvgftg6dYm5ndr1lHF3I71lFogxmTzgf3xNoIJF9AhgOQPgF9/dqF1LB5DyEpjxiA+5svlyDhPOCFhzpUklKTBymxPF17p1inx"
    b"f/hS/DSn5gSfj7ANRV7Puq2o+i0nx3WcM7v+iN4DHOY4bXoAv6MRSq7TQIODwLj124V0FLCyQyI1GVmvE6D5Wv0lUM1h5H8FGxwT"
    b"MtvRZZGF9tXjtQfH5MnI/wDF/vlC"
)

_SRC_LOCK = threading.Lock()
_SRC_NS = {}


def _load_src(key):
    """按需解压内嵌源，返回模块命名空间（每个源一份全局变量）。"""
    with _SRC_LOCK:
        if key in _SRC_NS:
            return _SRC_NS[key]
        name, blob = _EMBED[key]
        raw = zlib.decompress(base64.b64decode(blob)).decode('utf-8')
        ns = {'__name__': 'agg_src_' + key, '__file__': '<agg:%s>' % key}
        exec(compile(raw, '<agg:%s>' % key, 'exec'), ns)
        _SRC_NS[key] = ns
        if key == 'hg':
            # 红果源自带“官方取季”，默认预算 9s；这里压到 ~3s，先给壳一个能秒开的结果，
            # 源端会把截断结果只缓存 2 分钟，下次打开自动补全。ext 里可调 hg_season_budget。
            try:
                for fn in ('_hg_seasons', '_hg_official_seasons_merged'):
                    f = ns.get(fn)
                    if f is not None and getattr(f, '__defaults__', None):
                        f.__defaults__ = (2.5,)
            except Exception:
                pass
        return ns


def _new_spider(key, extend=''):
    ns = _load_src(key)
    cls = ns.get('Spider')
    inst = cls()
    try:
        inst.init(extend)
    except Exception:
        pass
    return inst


# =============================================================================
# 二、通用文本 / 季号 / 线路名处理
# =============================================================================
_CN_NUM = {'一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5, '六': 6,
           '七': 7, '八': 8, '九': 9, '十': 10}


def _cn_int(s):
    s = str(s or '').strip()
    if s.isdigit():
        return int(s)
    if len(s) == 1:
        return _CN_NUM.get(s, 0)
    if len(s) == 2 and s[0] == '十':
        return 10 + _CN_NUM.get(s[1], 0)
    if len(s) == 2 and s[1] == '十':
        return _CN_NUM.get(s[0], 0) * 10
    if len(s) == 3 and s[1] == '十':
        return _CN_NUM.get(s[0], 0) * 10 + _CN_NUM.get(s[2], 0)
    return 0


def cn_season(n):
    n = int(n or 0)
    if n <= 0:
        return ''
    digits = '零一二三四五六七八九'
    if n <= 10:
        return '第' + ('十' if n == 10 else digits[n]) + '季'
    if n < 20:
        return '第十' + digits[n - 10] + '季'
    if n < 100:
        a, b = divmod(n, 10)
        return '第' + digits[a] + '十' + (digits[b] if b else '') + '季'
    return '第%d季' % n


_SEASON_RES = [
    re.compile(r'第\s*([0-9]{1,3}|[一二三四五六七八九十]{1,3})\s*季'),
    re.compile(r'第\s*([0-9]{1,3}|[一二三四五六七八九十]{1,3})\s*部'),
    re.compile(r'(?i)\bseason\s*([0-9]{1,2})\b'),
    re.compile(r'(?i)\bS([0-9]{1,2})\s*E[0-9]{1,3}\b'),
    re.compile(r'([0-9]{1,2})\s*季'),
]
_TAIL_SEASON = re.compile(r'(?<![0-9])([0-9]{1,2})\s*$')
_NOISE = [
    re.compile(r'[（(\[【]\s*(4K|8K|HDR10?|HDR10\+|杜比视界|DV|蓝光|原盘|国粤双语|双字|中字|内嵌|无删减)[^)）】\]]*[)）】\]》]?', re.I),
    re.compile(r'\b4K\b|\b8K\b|\bHDR10?\+?\b|\bUHD\b|\bREMUX\b', re.I),
    re.compile(r'全\s*[0-9]{1,3}\s*集|更新\s*[0-9]{1,3}\s*集|连载中|全剧集|已完结'),
    re.compile(r'豆瓣\s*[0-9.]+\s*分?'),
    re.compile(u'完结季|最新季'),
    re.compile(r'[（(]\s*[0-9]{4}\s*[)）]'),
]


def base_title(name):
    """去掉季号、画质、集数等尾巴，得到用于跨源匹配的基础片名。"""
    s = re.sub(r'<[^>]*>', ' ', str(name or '')).strip()
    s = s.replace('$', ' ').replace('#', ' ')
    for rx in _NOISE:
        s = rx.sub(' ', s)
    s = s.strip(' -_·:：|')
    for rx in _SEASON_RES:
        m = rx.search(s)
        if m:
            s = (s[:m.start()] + ' ' + s[m.end():]).strip()
    s = re.sub(r'^[《【]|[》】]$', '', s.strip())
    s = re.sub(r'\s+', ' ', s).strip(' -_·:：|')
    s = re.sub(u'(?<=[\u4e00-\u9fa5])(?:[2-9]|[12][0-9]|30)$', '', s).strip()
    return s or str(name or '').strip()


def split_season(name):
    """返回 (基础片名, 季号, 是否识别到季号)。"""
    raw = str(name or '').strip()
    for rx in _SEASON_RES:
        m = rx.search(raw)
        if m:
            no = _cn_int(m.group(1))
            if 1 <= no <= 300:
                cleaned = (raw[:m.start()] + ' ' + raw[m.end():]).strip()
                cleaned = re.sub(u'^[《【]|[》】]$', '', cleaned).strip(' -_·:：|')
                base = base_title(raw)
                return (base or cleaned or raw, no, True)
    m = _TAIL_SEASON.search(raw)
    if m:
        no = int(m.group(1))
        # 只把 2~30 的尾巴当季号，避免 1980/2024 这类年份误判
        if 2 <= no <= 30 and len(raw) >= 3:
            return (base_title(raw), no, True)
    return (base_title(raw), 1, False)


def _norm_title(s):
    s = str(s or '').lower()
    s = re.sub(r'[\s《》【】\[\]()（）·,，.。:：!！?？\-_/\\|"\']', '', s)
    s = re.sub(u'第[0-9一二三四五六七八九十]{1,3}[季部]', '', s)
    s = re.sub(r'\b(4k|8k|hdr|uhd)\b', '', s)
    return s


def _year_int(v):
    try:
        return int(re.sub(r'\D', '', str(v or ''))[:4] or 0)
    except Exception:
        return 0


def _score_val(v):
    try:
        return float(re.sub(r'[^0-9.]', '', str(v or '')) or 0)
    except Exception:
        return 0.0


def title_match(a, b):
    na, nb = _norm_title(a), _norm_title(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    if len(na) >= 5 and len(nb) >= 5 and (na.startswith(nb) or nb.startswith(na) or na in nb or nb in na):
        return True
    return False


_PROVIDER_LEAD = re.compile(r'^\s*(?:AI\s*)?(?:4K|8K|2160P?|1080P?|720P?|蓝光|超清|高清|原画|HDR|杜比视界)\s*[-_·| ]+', re.I)
_PROVIDER_TAIL = re.compile(r'\s*[-_·| ]*(?:资源|线路|影视|专线|云播|网|专享\s*[A-Za-z]?)$', re.I)
_EP_CLEAN = re.compile(r'[$#]')


_EP_SNUM = re.compile(r'(?i)S(\d{1,2})\s*[-_]?\s*E?\d{1,4}')
_EP_CNUM = re.compile(r'第\s*([0-9]{1,3}|[一二三四五六七八九十]{1,3})\s*季')


def ep_season(title):
    s = str(title or '')
    m = _EP_SNUM.search(s)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 300:
            return n
    m = _EP_CNUM.search(s)
    if m:
        n = _cn_int(m.group(1))
        if 1 <= n <= 300:
            return n
    return 0


def slim_provider(flag):
    s = _EP_CLEAN.sub(' ', str(flag or '')).strip()
    s = re.sub(u'酒亓[·•]?', '', s)
    s = re.sub(r'^第[0-9一二三四五六七八九十]{1,3}[季部]\s*', '', s)
    s = re.sub(r'·\s*(普通话|國語|国语|粤语|粵語|英语|原声|中字)\s*', '', s)
    s = re.sub(r'^\s*(\d{1,3})\s*[-_]\s*', '', s)
    for _ in range(2):
        s = _PROVIDER_LEAD.sub('', s)
        s = _PROVIDER_TAIL.sub('', s)
    s = re.sub(r'专享\s*[A-Za-z]?$', '', s).strip()
    s = re.sub(r'\s+', ' ', s).strip(' -_·|')
    if re.search(u'UC', s, re.I):
        return 'UC免登'
    if u'夸克' in s:
        return '夸克免登'
    if '123' in s:
        return '123云盘'
    if u'全季连播' in s:
        return u'全季连播'
    s = re.sub(r'^\s*(?:1080|2160|720|480)\s*', '', s, flags=re.I)
    s = re.sub(r'\s*#?\s*\d+\s*$', '', s).strip()
    s = re.sub(r'\s*资源$', '', s).strip()
    return s or '默认'


def _fmt_remark(s):
    return re.sub(r'\s+', ' ', str(s or '')).strip(' ·|')


# =============================================================================
# 三、播放地址画质探测（真实取样：HLS 清单 / TS 首段 / MP4 moov / MKV Tracks）
# =============================================================================
PROBE_UA = 'okhttp/4.12.0'
PROBE_TIMEOUT = (6, 15)


def _pget(url, headers=None, rng=None):
    h = {'User-Agent': PROBE_UA}
    if headers:
        try:
            h.update({k: v for k, v in headers.items() if v})
        except Exception:
            pass
    if rng:
        h['Range'] = 'bytes=%d-%d' % rng
    return requests.get(url, headers=h, timeout=PROBE_TIMEOUT, stream=True)


def _pread(r, limit):
    buf = bytearray()
    try:
        for c in r.iter_content(65536):
            buf.extend(c)
            if len(buf) >= limit:
                break
    except Exception:
        pass
    try:
        r.close()
    except Exception:
        pass
    return bytes(buf)


def _plen(url, headers=None):
    try:
        r = _pget(url, headers, (0, 1))
        total = 0
        m = re.search(r'/(\d+)', r.headers.get('content-range') or '')
        if m:
            total = int(m.group(1))
        elif r.status_code == 200:
            total = int(r.headers.get('content-length') or 0)
        ctype = (r.headers.get('content-type') or '').split(';')[0].strip().lower()
        try:
            r.close()
        except Exception:
            pass
        return total, ctype
    except Exception:
        return 0, ''


_STREAM_INF = re.compile(r'#EXT-X-STREAM-INF:([^\n\r]+)')
_HLS_MEDIA = re.compile(r'#EXT-X-MEDIA:([^\n\r]+)')


def _hls_attrs(s):
    out = {}
    for k, v in re.findall(r'([A-Z0-9-]+)=("[^"]*"|[^,]*)', s):
        out[k] = v.strip('"')
    return out


def _probe_hls(url, headers=None):
    try:
        body = _pread(_pget(url, headers), 200000).decode('utf-8', 'replace')
    except Exception:
        return None
    if '#EXTM3U' not in body:
        return None
    info = {'source': 'hls', 'url': url}
    if '#EXT-X-STREAM-INF' in body:
        lines = [x.strip() for x in body.splitlines()]
        best = None
        for i, line in enumerate(lines):
            m = _STREAM_INF.match(line)
            if not m:
                continue
            a = _hls_attrs(m.group(1))
            nxt = ''
            for j in range(i + 1, min(i + 4, len(lines))):
                if lines[j] and not lines[j].startswith('#'):
                    nxt = lines[j]
                    break
            try:
                w, h = [int(x) for x in (a.get('RESOLUTION', '0x0').lower().split('x'))[:2]]
            except Exception:
                w = h = 0
            score = (h, int(a.get('BANDWIDTH') or 0))
            if best is None or score > best[0]:
                best = (score, w, h, nxt, a)
        if best:
            _, w, h, nxt, a = best
            info['width'], info['height'] = w, h
            info['bandwidth'] = int(a.get('BANDWIDTH') or 0)
            info['video_range'] = a.get('VIDEO-RANGE', '')
            codecs = (a.get('CODECS') or '').lower()
            if 'ec-3' in codecs:
                info['acodec'] = 'eac3'
            elif 'ac-3' in codecs:
                info['acodec'] = 'ac3'
            for mm in _HLS_MEDIA.finditer(body):
                am = _hls_attrs(mm.group(1))
                if am.get('TYPE', '').upper() == 'AUDIO':
                    try:
                        ch = int(am.get('CHANNELS') or 0)
                        if 0 < ch <= 8:
                            info['channels'] = max(info.get('channels') or 0, ch)
                    except Exception:
                        pass
                    c2 = (am.get('CODECS') or '').lower()
                    if 'ec-3' in c2:
                        info['acodec'] = 'eac3'
                    elif 'ac-3' in c2:
                        info['acodec'] = 'ac3'
            if nxt:
                seg = _probe_hls_media(urllib_join(url, nxt), headers)
                if seg:
                    for k in ('vcodec', 'acodec', 'channels', 'transfer', 'primaries', 'hdr'):
                        if seg.get(k) and not info.get(k):
                            info[k] = seg[k]
                    if (seg.get('height') or 0) > (info.get('height') or 0):
                        info['height'] = seg['height']
                        info['width'] = seg.get('width') or info.get('width')
            return _grade(info)
    seg = _probe_hls_media(url, headers, body)
    if seg:
        seg['source'] = 'hls'
        return _grade(seg)
    return None


def urllib_join(base, path):
    try:
        from urllib.parse import urljoin
        return urljoin(base, path)
    except Exception:
        return path


def _probe_hls_media(url, headers=None, body=None):
    if body is None:
        try:
            body = _pread(_pget(url, headers), 200000).decode('utf-8', 'replace')
        except Exception:
            return None
    if '#EXT-X-STREAM-INF' in body:
        return None
    segs = [x.strip() for x in body.splitlines() if x.strip() and not x.startswith('#')]
    if not segs:
        return None
    for i in range(min(2, len(segs))):
        try:
            data = _pread(_pget(urllib_join(url, segs[i]), headers, (0, 2 * 1024 * 1024 - 1)),
                          2 * 1024 * 1024)
        except Exception:
            continue
        if not data:
            continue
        if data[:1] == b'\x47' or b'\x47' in data[:376]:
            info = _parse_ts(data)
            if info:
                return info
        if data[:4] == b'\x1aE\xdf\xa3':
            info = _parse_mkv(data)
            if info:
                return info
        if b'ftyp' in data[:32]:
            info = _parse_mp4(data)
            if info:
                return info
    return None


def _ts_packets(data):
    start = data.find(b'\x47')
    if start < 0:
        return []
    return [data[i:i + 188] for i in range(start, len(data) - 187, 188)]


def _ts_section(pkts, pid, table_id):
    sec = b''
    for p in pkts:
        if not p or len(p) != 188:
            continue
        if ((p[1] & 0x1F) << 8 | p[2]) != pid:
            continue
        pusi = bool(p[1] & 0x40)
        afc = (p[3] >> 4) & 0x3
        off = 4
        if afc in (2, 3):
            off += 1 + p[4]
        if off >= 188:
            continue
        if pusi:
            off += 1 + p[off]
            sec = b''
        sec += p[off:]
        if len(sec) >= 3:
            if sec[0] != table_id:
                sec = b''
                continue
            length = ((sec[1] & 0x0F) << 8 | sec[2]) + 3
            if len(sec) >= length:
                return sec[:length]
    return b''


def _parse_pat(pkts):
    sec = _ts_section(pkts, 0, 0x00)
    if sec and len(sec) >= 12:
        return ((sec[10] & 0x1F) << 8) | sec[11]
    return 0


def _parse_pmt(pkts, pid):
    sec = _ts_section(pkts, pid, 0x02)
    if not sec or len(sec) < 16:
        return []
    info_len = ((sec[10] & 0x0F) << 8) | sec[11]
    pos = 12 + info_len
    end = len(sec) - 4
    streams = []
    while pos + 5 <= end:
        st = sec[pos]
        epid = ((sec[pos + 1] & 0x1F) << 8) | sec[pos + 2]
        es_len = ((sec[pos + 3] & 0x0F) << 8) | sec[pos + 4]
        streams.append((epid, st))
        pos += 5 + es_len
    return streams


def _es_from_pes(pkts, pid, limit=400000):
    out = bytearray()
    started = False
    for p in pkts:
        if len(p) != 188:
            continue
        if ((p[1] & 0x1F) << 8 | p[2]) != pid:
            continue
        afc = (p[3] >> 4) & 0x3
        off = 4
        if afc in (2, 3):
            off += 1 + p[4]
        if off >= 188:
            continue
        if p[1] & 0x40:
            if off + 9 > 188:
                continue
            off += 9 + p[off + 8]
            started = True
        if started and off < 188:
            out.extend(p[off:])
            if len(out) > limit:
                break
    return bytes(out)


class _BR(object):
    __slots__ = ('d', 'i', 'n')

    def __init__(self, data):
        self.d = data
        self.i = 0
        self.n = len(data) * 8

    def u(self, n):
        v = 0
        if n <= 0:
            return 0
        if self.i + n > self.n:
            self.i = self.n
            return 0
        for _ in range(n):
            byte = self.d[self.i >> 3]
            v = (v << 1) | ((byte >> (7 - (self.i & 7))) & 1)
            self.i += 1
        return v

    def ue(self):
        zeros = 0
        while self.i < self.n and self.u(1) == 0:
            zeros += 1
            if zeros > 31:
                return 0
        if zeros == 0:
            return 0
        return (1 << zeros) - 1 + self.u(zeros)

    def se(self):
        v = self.ue()
        return (v + 1) // 2 if v & 1 else -(v // 2)


def _h264_sps(es):
    for marker in (b'\x00\x00\x00\x01', b'\x00\x00\x01'):
        pos = es.find(marker)
        while pos >= 0:
            st = pos + len(marker)
            if st + 3 < len(es) and (es[st] & 0x1F) == 7:
                raw = es[st:].replace(b'\x00\x00\x03', b'\x00\x00')
                try:
                    out = _h264_sps_parse(raw[1:])
                    if out.get('width'):
                        return out
                except Exception:
                    pass
            pos = es.find(marker, pos + 1)
    return {}


def _h264_sps_parse(b):
    br = _BR(b)
    profile = br.u(8)
    br.u(8)
    br.u(8)
    br.ue()
    chroma = 1
    if profile in (100, 110, 122, 244, 44, 83, 86, 118, 128, 138, 139, 134, 135):
        chroma = br.ue() or 1
        if chroma == 3:
            br.u(1)
        br.ue()
        br.ue()
        br.u(1)
        if br.u(1):
            for i in range(8 if chroma != 3 else 12):
                if br.u(1):
                    _skip_scaling(br, 16 if i < 6 else 64)
    br.ue()
    poc = br.ue()
    if poc == 0:
        br.ue()
    elif poc == 1:
        br.u(1)
        br.se()
        br.se()
        for _ in range(min(br.ue(), 256)):
            br.se()
    br.ue()
    br.u(1)
    w_mbs = br.ue() + 1
    h_map = br.ue() + 1
    frame_only = br.u(1)
    if not frame_only:
        br.u(1)
    br.u(1)
    crop = [0, 0, 0, 0]
    if br.u(1):
        crop = [br.ue(), br.ue(), br.ue(), br.ue()]
    sub_w = 2 if chroma in (1, 2) else 1
    sub_h = 2 if chroma == 1 else 1
    out = {'vcodec': 'h264', 'width': w_mbs * 16 - (crop[0] + crop[1]) * sub_w,
           'height': h_map * 16 * (2 - frame_only) - (crop[2] + crop[3]) * sub_h * (2 - frame_only)}
    if br.u(1):
        out.update(_vui(br))
    return out


def _skip_scaling(br, size):
    last = 8
    nxt = 8
    for _ in range(size):
        if nxt != 0:
            nxt = (last + br.se() + 256) % 256
        last = nxt if nxt != 0 else last


def _vui(br):
    out = {}
    if br.u(1):
        ar = br.u(8)
        if ar == 255:
            br.u(16)
            br.u(16)
    if br.u(1):
        br.u(1)
    if br.u(1):
        br.u(3)
        br.u(1)
        if br.u(1):
            out['primaries'] = br.u(8)
            out['transfer'] = br.u(8)
            out['matrix'] = br.u(8)
    return out


def _hevc_sps(es):
    for marker in (b'\x00\x00\x00\x01', b'\x00\x00\x01'):
        pos = es.find(marker)
        while pos >= 0:
            st = pos + len(marker)
            if st + 2 < len(es) and ((es[st] >> 1) & 0x3F) == 33:
                raw = es[st:].replace(b'\x00\x00\x03', b'\x00\x00')
                try:
                    out = _hevc_sps_parse(raw[2:])
                    if out.get('width'):
                        return out
                except Exception:
                    pass
            pos = es.find(marker, pos + 1)
    return {}


def _hevc_sps_parse(b):
    br = _BR(b)
    br.u(4)
    max_sub = br.u(3)
    br.u(1)
    br.u(2)
    br.u(1)
    br.u(5)
    br.u(32)
    br.u(48)
    br.u(8)
    pflags, lflags = [], []
    for _ in range(max_sub):
        pflags.append(br.u(1))
        lflags.append(br.u(1))
    if max_sub > 0:
        for _ in range(max_sub, 8):
            br.u(2)
    for i in range(max_sub):
        if pflags[i]:
            br.u(88)
        if lflags[i]:
            br.u(8)
    br.ue()
    chroma = br.ue() or 1
    if chroma == 3:
        br.u(1)
    w = br.ue()
    h = br.ue()
    crop = [0, 0, 0, 0]
    if br.u(1):
        crop = [br.ue(), br.ue(), br.ue(), br.ue()]
    sub_w, sub_h = ((2, 2) if chroma == 1 else (2, 1) if chroma == 2 else (1, 1))
    w -= (crop[0] + crop[1]) * sub_w
    h -= (crop[2] + crop[3]) * sub_h
    for _ in range(3):
        br.ue()
    br.u(1)
    sub_flag = br.u(1)
    for _ in range(max_sub if sub_flag else 1):
        br.ue()
        br.ue()
        br.ue()
    for _ in range(6):
        br.ue()
    if br.u(1):
        if br.u(1):
            _skip_scaling_list_data(br)
    br.u(1)
    br.u(1)
    if br.u(1):
        br.u(4)
        br.u(4)
        br.ue()
        br.ue()
        br.u(1)
    num_delta = []
    for i in range(min(br.ue(), 64)):
        num_delta.append(_skip_st_ref_pic_set(br, i, num_delta))
    if br.u(1):
        for _ in range(min(br.ue(), 64)):
            br.u(8)
            br.u(1)
    br.u(1)
    br.u(1)
    out = {'vcodec': 'hevc', 'width': w, 'height': h}
    if br.u(1):
        out.update(_vui(br))
    return out


def _skip_st_ref_pic_set(br, idx, num_delta):
    if idx != 0 and br.u(1):
        if idx == 0:
            br.ue()
        else:
            br.u(1)
            br.ue()
        n = num_delta[-1] if num_delta else 0
        for _ in range(n + 1):
            if not br.u(1):
                br.u(1)
        return n + 1
    neg = min(br.ue(), 64)
    pos = min(br.ue(), 64)
    for _ in range(neg):
        br.ue()
        br.u(1)
    for _ in range(pos):
        br.ue()
        br.u(1)
    return neg + pos


def _skip_scaling_list_data(br):
    for size_id in range(4):
        for _ in range(6 if size_id != 3 else 2):
            if br.u(1):
                coef = min(64, 1 << (4 + (size_id << 1)))
                if size_id > 1:
                    br.se()
                for _ in range(coef):
                    br.se()
            else:
                br.ue()


def _aac_channels(es):
    for i in range(0, min(len(es) - 7, 600)):
        if es[i] == 0xFF and (es[i + 1] & 0xF0) == 0xF0:
            cfg = (es[i + 2] >> 2) & 0x0F
            return {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 8}.get(cfg, 0)
    return 0


def _ac3_channels(es, eac3=False):
    for i in range(0, min(len(es) - 8, 600)):
        if es[i] == 0x0B and es[i + 1] == 0x77:
            if eac3:
                acmod = (es[i + 4] >> 5) & 0x7
                lfe = (es[i + 5] >> 7) & 0x1
            else:
                acmod = (es[i + 4] >> 3) & 0x7
                pos_bit = (i + 4) * 8 + 6
                lfe = (es[pos_bit >> 3] >> (7 - (pos_bit & 7))) & 1
            return {0: 2, 1: 2, 2: 3, 3: 3, 4: 3, 5: 4, 6: 4, 7: 5}.get(acmod, 2) + (1 if lfe else 0)
    return 0


def _parse_ts(data):
    pkts = _ts_packets(data)
    if not pkts:
        return None
    pmt_pid = _parse_pat(pkts)
    if not pmt_pid:
        return None
    streams = _parse_pmt(pkts, pmt_pid)
    if not streams:
        return None
    info = {'source': 'ts'}
    vid_pids = [pid for pid, st in streams if st in (0x02, 0x1B, 0x24, 0x42)]
    for pid in vid_pids[:2]:
        es = _es_from_pes(pkts, pid)
        sp = _h264_sps(es) or _hevc_sps(es)
        if sp.get('width'):
            info.update(sp)
            break
    for pid, st in streams:
        if st not in (0x0F, 0x11, 0x81, 0x87, 0x06, 0x24):
            continue
        es = _es_from_pes(pkts, pid)
        if st == 0x81:
            ch = _ac3_channels(es, False)
            info.setdefault('acodec', 'ac3')
        elif st == 0x87:
            ch = _ac3_channels(es, True)
            info.setdefault('acodec', 'eac3')
        elif st == 0x06:
            ch = _ac3_channels(es, False)
            if ch:
                info.setdefault('acodec', 'ac3')
            else:
                ch = _aac_channels(es)
                if ch:
                    info.setdefault('acodec', 'aac')
        else:
            ch = _aac_channels(es)
            if ch:
                info.setdefault('acodec', 'aac')
        if ch and 0 < ch <= 8:
            info['channels'] = max(info.get('channels') or 0, ch)
    if not info.get('width') and not info.get('channels'):
        return None
    return info


def _walk_boxes(data, start=0, end=None):
    if end is None:
        end = len(data)
    pos = start
    out = []
    while pos + 8 <= end:
        size = int.from_bytes(data[pos:pos + 4], 'big')
        typ = data[pos + 4:pos + 8]
        hdr = 8
        if size == 1:
            if pos + 16 > end:
                break
            size = int.from_bytes(data[pos + 8:pos + 16], 'big')
            hdr = 16
        elif size == 0:
            size = end - pos
        if size < hdr or pos + size > end:
            break
        out.append((typ, pos + hdr, pos + size))
        pos += size
    return out


def _find_box(data, typ, start=0, end=None):
    for t, s, e in _walk_boxes(data, start, end):
        if t == typ:
            return s, e
    return None


_MP4_BOXES = set([b'moov', b'trak', b'mdia', b'minf', b'stbl', b'edts', b'udta', b'dinf'])


def _find_deep(data, typ, start, end, depth=5):
    for t, s, e in _walk_boxes(data, start, end):
        if t == typ:
            return s, e
        if t in _MP4_BOXES and depth > 0:
            r = _find_deep(data, typ, s, e, depth - 1)
            if r:
                return r
    return None


def _parse_mp4(data):
    info = {'source': 'mp4'}
    moov = _find_box(data, b'moov')
    if not moov:
        return None
    for trak in _walk_boxes(data, moov[0], moov[1]):
        if trak[0] != b'trak':
            continue
        hdlr = _find_deep(data, b'hdlr', trak[1], trak[2])
        kind = data[hdlr[0] + 8:hdlr[0] + 12] if hdlr and hdlr[1] - hdlr[0] >= 12 else b''
        stsd = _find_deep(data, b'stsd', trak[1], trak[2])
        if not stsd:
            continue
        for et, es, ee in _walk_boxes(data, stsd[0] + 8, stsd[1]):
            if kind == b'vide':
                info.setdefault('vcodec', {b'avc1': 'h264', b'avc3': 'h264', b'hvc1': 'hevc',
                                           b'hev1': 'hevc', b'dvh1': 'hevc', b'dvhe': 'hevc',
                                           b'av01': 'av1', b'vp09': 'vp9'}.get(et, et.decode('latin-1')))
                raw = data[es:ee]
                if len(raw) >= 28:
                    w = int.from_bytes(raw[24:26], 'big')
                    h = int.from_bytes(raw[26:28], 'big')
                    if w and h:
                        info['width'], info['height'] = w, h
                if et in (b'dvh1', b'dvhe'):
                    info['hdr'] = 'DV'
                for bt, bs, be in _walk_boxes(data, es + 78, ee):
                    if bt == b'colr' and be - bs >= 10:
                        info['primaries'] = int.from_bytes(data[bs + 4:bs + 6], 'big')
                        info['transfer'] = int.from_bytes(data[bs + 6:bs + 8], 'big')
                    elif bt in (b'mdcv', b'clli'):
                        info['hdr'] = info.get('hdr') or 'HDR10'
                    elif bt in (b'dvcC', b'dvvC'):
                        info['hdr'] = 'DV'
            elif kind == b'soun':
                codec = {b'mp4a': 'aac', b'ac-3': 'ac3', b'ec-3': 'eac3', b'dac3': 'eac3',
                         b'dec3': 'eac3', b'mlpa': 'truehd', b'dtsc': 'dts'}.get(et, '')
                if codec:
                    info.setdefault('acodec', codec)
                raw = data[es:ee]
                if len(raw) >= 18:
                    ch = int.from_bytes(raw[16:18], 'big')
                    if 0 < ch <= 8:
                        info['channels'] = max(info.get('channels') or 0, ch)
    if not info.get('width') and not info.get('channels'):
        return None
    return info


def _eid(data, pos):
    b = data[pos]
    for n in range(1, 5):
        if b & (0x80 >> (n - 1)):
            return int.from_bytes(data[pos:pos + n], 'big'), n
    return 0, 1


def _esize(data, pos):
    b = data[pos]
    n = 1
    mask = 0x80
    while n <= 8:
        if b & mask:
            break
        mask >>= 1
        n += 1
    if n > 8 or pos + n > len(data):
        return 0, 1, True
    raw = data[pos:pos + n]
    val = raw[0] & (0xFF >> n)
    unknown = val == (0xFF >> n)
    for i in range(1, n):
        val = (val << 8) | raw[i]
    return val, n, unknown


def _ebml_iter(data, start, end):
    pos = start
    while pos + 2 < end:
        eid, n1 = _eid(data, pos)
        if eid == 0:
            break
        size, n2, unknown = _esize(data, pos + n1)
        body = pos + n1 + n2
        if body >= end:
            break
        if unknown:
            yield eid, body, end, True
            pos = body
            continue
        if size <= 0 or body + size > end:
            pos = body
            continue
        yield eid, body, body + size, False
        pos = body + size


def _parse_mkv(data):
    if data[:4] != b'\x1aE\xdf\xa3':
        return None
    info = {'source': 'mkv'}
    tracks = None
    for eid, s, e, unk in _ebml_iter(data, 0, len(data)):
        if eid == 0x18538067:
            for eid2, s2, e2, unk2 in _ebml_iter(data, s, e):
                if eid2 == 0x1654AE6B:
                    tracks = (s2, e2)
                    break
                if eid2 == 0x1F43B675:
                    break
            break
    if not tracks:
        return None
    for eid, s, e, unk in _ebml_iter(data, tracks[0], tracks[1]):
        if eid != 0xAE:
            continue
        ttype, codec, ch = 0, '', 0
        vinfo = {}
        for eid2, s2, e2, unk2 in _ebml_iter(data, s, e):
            if eid2 == 0x83 and e2 > s2:
                ttype = int.from_bytes(data[s2:e2], 'big')
            elif eid2 == 0x86:
                codec = data[s2:e2].decode('utf-8', 'replace')
            elif eid2 == 0xE0:
                for eid3, s3, e3, unk3 in _ebml_iter(data, s2, e2):
                    if eid3 == 0xB0:
                        vinfo['width'] = int.from_bytes(data[s3:e3], 'big')
                    elif eid3 == 0xBA:
                        vinfo['height'] = int.from_bytes(data[s3:e3], 'big')
                    elif eid3 == 0x55B0:
                        for eid4, s4, e4, unk4 in _ebml_iter(data, s3, e3):
                            if eid4 == 0x55BA:
                                vinfo['transfer'] = int.from_bytes(data[s4:e4], 'big')
                            elif eid4 == 0x55BB:
                                vinfo['primaries'] = int.from_bytes(data[s4:e4], 'big')
                            elif eid4 == 0x55BC:
                                vinfo['matrix'] = int.from_bytes(data[s4:e4], 'big')
                            elif eid4 == 0x55D0:
                                vinfo['hdr'] = 'HDR10'
            elif eid2 == 0xE1:
                for eid3, s3, e3, unk3 in _ebml_iter(data, s2, e2):
                    if eid3 == 0x9F:
                        ch = int.from_bytes(data[s3:e3], 'big')
        if ttype == 1:
            info.update(vinfo)
            info['vcodec'] = {'V_MPEGH/ISO/HEVC': 'hevc', 'V_MPEG4/ISO/AVC': 'h264',
                              'V_AV1': 'av1'}.get(codec, codec)
            if 'dv' in codec.lower():
                info['hdr'] = 'DV'
        elif ttype == 2:
            info.setdefault('acodec', {'A_EAC3': 'eac3', 'A_AC3': 'ac3', 'A_AAC': 'aac',
                                       'A_DTS': 'dts', 'A_TRUEHD': 'truehd',
                                       'A_FLAC': 'flac'}.get(codec, codec.lower().replace('a_', '')))
            if ch:
                info['channels'] = max(info.get('channels') or 0, ch)
    if not info.get('width') and not info.get('channels'):
        return None
    return info


_TAG_RE = re.compile(r'(4k|2160p|1080p|720p|hdr10|hdr|dolby|dts|remux|蓝光|原盘|bluray|uhd)', re.I)


def _grade(info):
    if not info:
        return info
    w = int(info.get('width') or 0)
    h = int(info.get('height') or 0)
    if not h and w:
        h = int(w * 9 / 16.0)
    if w >= 3000 or h >= 1800:
        res = '4K'
    elif w >= 1800 or h >= 1000:
        res = '1080P'
    elif w >= 1200 or h >= 700:
        res = '720P'
    elif w or h:
        res = '%dP' % (h or int(w * 9 / 16.0))
    else:
        res = ''
    info['res'] = res
    tr = int(info.get('transfer') or 0)
    pr = int(info.get('primaries') or 0)
    hdr = info.get('hdr') or ''
    if not hdr:
        if tr == 16:
            hdr = 'HDR10'
        elif tr == 18:
            hdr = 'HLG'
        elif pr == 9 and tr in (16, 18):
            hdr = 'HDR10'
    info['hdr'] = hdr
    ch = int(info.get('channels') or 0)
    ac = (info.get('acodec') or '').lower()
    if ch >= 6 and ac == 'eac3':
        audio = 'DD+%d.1' % (8 if ch >= 8 else 6) if ch >= 8 else 'DD+5.1'
    elif ch >= 6 and ac == 'ac3':
        audio = '杜比5.1'
    elif ch >= 6 and ac == 'truehd':
        audio = 'TrueHD%d.1' % (8 if ch >= 8 else 6)
    elif ch >= 6 and ac == 'dts':
        audio = 'DTS%d.1' % (8 if ch >= 8 else 6)
    elif ch >= 6:
        audio = '%d声道' % ch
    else:
        audio = ''
    info['audio_label'] = audio
    tags = []
    if res:
        tags.append(res)
    if hdr:
        tags.append(hdr)
    if audio:
        tags.append(audio)
    info['tags'] = tags
    info['label'] = '·'.join(tags)
    info['score'] = (3000 if res == '4K' else 1000 if res == '1080P' else 600 if res == '720P' else 0) \
        + (200 if hdr else 0) + (60 if ch >= 6 else 0)
    return info


def probe_url(url, headers=None):
    if not url:
        return None
    low = url.split('?')[0].lower()
    info = None
    if low.endswith('.m3u8') or low.endswith('.m3u'):
        info = _probe_hls(url, headers)
    elif re.search(r'\.(mp4|mkv|ts|mov|m4v|flv|avi|wmv|webm|rmvb)$', low):
        total, ctype = _plen(url, headers)
        info = _probe_binary(url, headers, total, ctype)
    else:
        total, ctype = _plen(url, headers)
        if 'mpegurl' in (ctype or ''):
            info = _probe_hls(url, headers)
        else:
            info = _probe_binary(url, headers, total, ctype)
    return _grade(info) if info else None


def _probe_binary(url, headers, total, ctype):
    try:
        head = _pread(_pget(url, headers, (0, 4 * 1024 * 1024 - 1)), 4 * 1024 * 1024)
    except Exception:
        return None
    if not head:
        return None
    if head[:4] == b'\x1aE\xdf\xa3':
        info = _parse_mkv(head)
        if info is None:
            try:
                info = _parse_mkv(_pread(_pget(url, headers, (0, 8 * 1024 * 1024 - 1)),
                                         8 * 1024 * 1024))
            except Exception:
                info = None
        return info
    if b'ftyp' in head[:64]:
        info = _parse_mp4(head)
        if info is None:
            info = _mp4_from_tail(url, headers, total, head)
        return info
    if head[:1] == b'\x47' or b'\x47' in head[:376]:
        return _parse_ts(head)
    return None


def _mp4_from_tail(url, headers, total, head):
    """moov 在文件尾的大 MP4（常见 2GB 以上、未 faststart）也能读到轨道信息。"""
    if total and total > len(head):
        for mb in (8, 24):
            try:
                start = max(len(head), total - mb * 1024 * 1024)
                tail = _pread(_pget(url, headers, (start, total - 1)), mb * 1024 * 1024)
            except Exception:
                continue
            if not tail:
                continue
            info = _parse_mp4(tail)
            if info:
                return info
            idx = tail.find(b'moov')
            if idx >= 4:
                mstart = start + idx - 4
                msize = int.from_bytes(tail[idx - 4:idx], 'big')
                if msize == 1 and idx + 8 <= len(tail):
                    msize = int.from_bytes(tail[idx + 4:idx + 12], 'big') + 16
                if 0 < msize <= 96 * 1024 * 1024:
                    try:
                        box = _pread(_pget(url, headers, (mstart, mstart + msize - 1)), msize)
                        info = _parse_mp4(box)
                        if info:
                            return info
                    except Exception:
                        pass
    return None

def speed_mbps(url, headers=None):
    """拉 1MB 取样算下载速度（MB/s），用于判断 4K 码率吃不吃得下。"""
    if not url:
        return 0
    try:
        t0 = time.time()
        r = _pget(url, headers, (0, 1024 * 1024 - 1))
        data = _pread(r, 1024 * 1024)
        dt = max(0.01, time.time() - t0)
        return round(len(data) / 1048576.0 / dt, 2)
    except Exception:
        return 0


def probe_quick(url, name='', headers=None):
    """轻量判级：先看地址里的 q=/HDR 标记（红果就是 q=1080），m3u8 再读 master，
    不拉 MP4/MKV 文件头，所以基本 0.2–0.6s。"""
    if not url:
        return None
    tags, h = [], 0
    m = re.search(r'[?&]q=(\d{3,4})', url)
    if m:
        v = int(m.group(1))
        if v >= 2000:
            tags.append('4K')
            h = 2160
        elif v >= 1000:
            tags.append('1080P')
            h = 1080
        elif v >= 700:
            tags.append('720P')
            h = 720
    nm = str(url) + ' ' + str(name or '')
    if re.search(r'hdr10', nm, re.I):
        tags.append('HDR10')
    elif re.search(r'hdr', nm, re.I):
        tags.append('HDR')
    if re.search(r'dolby\s*vision|杜比视界|dovi', nm, re.I):
        tags.append('DV')
    if tags:
        return {'source': 'quick', 'tags': tags, 'label': '·'.join(tags), 'height': h,
                'score': 3000 if h >= 2160 else (1200 if h >= 1080 else 900)}
    low = str(url).split('?')[0].lower()
    if low.endswith('.m3u8') or low.endswith('.m3u'):
        info = _probe_hls(url, headers)
        return _grade(info) if info else None
    return None


def probe_item(url, name='', headers=None):
    info = probe_url(url, headers)
    if info and (info.get('tags') or info.get('width')):
        return info
    if name:
        tags = []
        if re.search(r'4k|2160p|uhd', name, re.I):
            tags.append('4K')
        if re.search(r'hdr10', name, re.I):
            tags.append('HDR10')
        elif re.search(r'hdr', name, re.I):
            tags.append('HDR')
        if re.search(r'dolby\s*vision|杜比视界', name, re.I):
            tags.append('DV')
        if tags:
            return {'source': 'name', 'tags': tags, 'label': '·'.join(tags),
                    'height': 2160 if '4K' in tags else 0,
                    'score': 3000 if '4K' in tags else 1200}
    return None


# =============================================================================
# 四、五个源的适配器
# =============================================================================
SRC_NAME = {'yt': '影探', 'sj': '搜剧', 'xg': '星光', 'wp': '网盘', 'hg': '红果', 'xy': '新云'}
SRC_ORDER = ['yt', 'sj', 'xy', 'wp', 'xg', 'hg']


def _yt_cls_of(name):
    """影探导航里各种别名（国漫 / 欧美剧 / 恐怖片 / 记录片…）归到统一大类。"""
    n = str(name or '')
    if u'少儿' in n:
        return 'kids'
    if u'综艺' in n or u'国综' in n:
        return 'variety'
    if u'短剧' in n:
        return 'short'
    if u'记录' in n or u'纪录' in n:
        return 'doc'
    if u'漫' in n or u'动画' in n:
        return 'anime'
    if u'剧' in n:
        return 'tv'
    if u'电影' in n or u'片' in n or u'好莱坞' in n or u'武侠' in n:
        return 'movie'
    return None


class Adapter(object):
    key = ''
    supports = ()
    filters = ()        # 该源支持的二级筛选：cls（题材）/ area（地区）/ year（年份）/ ch（频道）

    def __init__(self, agg):
        self.agg = agg
        self.s = None
        self.lock = threading.Lock()
        self.dead_until = 0
        self.dead_hits = 0
        self.last_err = ''

    def alive(self):
        return time.time() >= self.dead_until

    def mark_dead(self, secs=300):
        self.dead_hits += 1
        self.dead_until = time.time() + secs

    def ok(self):
        self.dead_hits = 0

    def call(self, fn, *a, **kw):
        if not self.alive():
            raise RuntimeError('circuit-open')
        try:
            return fn(*a, **kw)
        except Exception as e:
            self.last_err = '%s: %s' % (type(e).__name__, e)
            self.mark_dead(120 if self.dead_hits < 2 else 600)
            raise

    def get(self):
        with self.lock:
            if self.s is None:
                self.s = self._spawn()
            return self.s

    def _spawn(self):
        return _new_spider(self.key, self.agg.opt.get(self.key + '_ext', ''))

    def ext_in(self, ext):
        """把聚合层的统一筛选翻成该源认识的关键字；源不支持的维度直接丢掉。"""
        return {}

    def catalog(self, cls, page, ext):
        return []

    def hot(self, page):
        return []

    def search(self, key, page):
        return []

    def detail(self, raw):
        return None

    def play(self, flag, pid):
        return {}


class YingTan(Adapter):
    key = 'yt'
    supports = ('movie', 'tv', 'anime', 'variety', 'short', 'doc', 'kids')
    filters = ('cls', 'area', 'year')
    TID = {'movie': '1', 'tv': '21', 'anime': '23', 'variety': '24', 'short': '22', 'doc': ''}

    def _spawn(self):
        return _new_spider('yt', '')

    def ext_in(self, ext):
        out = {}
        m = {'cls': 'class', 'area': 'area', 'year': 'year'}
        for k, v in (ext or {}).items():
            if v and k in m:
                out[m[k]] = AREA_ALIAS.get(v, v) if k == 'area' else v
        return out

    def catalog(self, cls, page, ext):
        tid = self.TID.get(cls)
        if not tid:
            return []
        d = self.call(self.get().categoryContent, tid, str(page), None, self.ext_in(ext))
        self.ok()
        out = []
        for v in (d.get('list') or []):
            out.append(self._norm(v))
        return out

    @staticmethod
    def _norm(v):
        return {'vod_id': str(v.get('vod_id') or ''),
                'vod_name': _fmt_remark(v.get('vod_name')),
                'vod_pic': v.get('vod_pic') or '',
                'vod_remarks': _fmt_remark(v.get('vod_remarks')),
                'vod_year': str(v.get('vod_year') or ''),
                'vod_score': str(v.get('vod_score') or v.get('score') or ''),
                'type_name': v.get('vod_class') or v.get('type_name') or ''}

    def catalog_by_tid(self, tid, page, ext=None):
        d = self.call(self.get().categoryContent, str(tid), str(page), None, self.ext_in(ext))
        self.ok()
        return [self._norm(v) for v in (d.get('list') or [])]

    def hot(self, page):
        if page > 1:
            return self.catalog('movie', page, {})
        d = self.call(self.get().homeVideoContent)
        self.ok()
        return [self._norm(v) for v in (d.get('list') or [])]

    def search(self, key, page):
        d = self.call(self.get().searchContent, key, False, str(page))
        self.ok()
        return [self._norm(v) for v in (d.get('list') or [])]

    def detail(self, raw):
        d = self.call(self.get().detailContent, [raw])
        self.ok()
        lst = d.get('list') or []
        return lst[0] if lst else None

    def play(self, flag, pid):
        return self.call(self.get().playerContent, flag, pid, {}) or {}


class Souju(Adapter):
    key = 'sj'
    supports = ('movie', 'tv', 'anime', 'variety', 'doc', 'short')
    KIND = {'movie': 'movie', 'tv': 'series', 'anime': 'anime', 'variety': 'variety',
            'doc': 'documentary', 'short': 'short_drama'}

    def _spawn(self):
        return _new_spider('sj', json.dumps({'direct_m3u8': True}))

    def _norm(self, v):
        return {'vod_id': str(v.get('vod_id') or ''),
                'vod_name': _fmt_remark(v.get('vod_name')),
                'vod_pic': v.get('vod_pic') or '',
                'vod_remarks': _fmt_remark(v.get('vod_remarks')),
                'vod_year': str(v.get('vod_year') or ''),
                'vod_score': str(v.get('vod_score') or v.get('score') or ''),
                'type_name': v.get('type_name') or ''}

    def catalog(self, cls, page, ext):
        kind = self.KIND.get(cls)
        if not kind:
            return []
        d = self.call(self.get().categoryContent, 'kind:' + kind, page, None, ext or {})
        self.ok()
        return [self._norm(v) for v in (d.get('list') or [])]

    def hot(self, page):
        if page > 1:
            return self.catalog('movie', page, {})
        d = self.call(self.get().homeContent, None)
        self.ok()
        return [self._norm(v) for v in (d.get('list') or [])]

    def search(self, key, page):
        d = self.call(self.get().searchContent, key, False, str(page))
        self.ok()
        return [self._norm(v) for v in (d.get('list') or [])]

    def seasons(self, vid):
        s = self.get()
        data = self.call(s._get_json, '/v1/catalog/' + _quote(vid))
        self.ok()
        out = []
        for it in (data.get('seasons') or []):
            if not isinstance(it, dict):
                continue
            no = int(it.get('season_number') or 0)
            sid = it.get('variant_id') or it.get('id') or ''
            if sid:
                out.append((no or 1, str(sid), it.get('title') or ''))
        return out

    def detail(self, raw):
        s = self.get()
        data = self.call(s._get_json, '/v1/catalog/' + _quote(raw))
        if not data or not data.get('title'):
            self.ok()
            return None
        eps = s._episodes(raw, data)
        labels = s._line_labels(eps[0]['token']) if eps else ['默认线路']
        bodies = []
        for _ in labels:
            cells = []
            for i, e in enumerate(eps):
                title = s._clean(e.get('title')) or ('第%d集' % (i + 1))
                cells.append('%s$%s' % (re.sub(r'[$#]', ' ', title), e['token']))
            bodies.append('#'.join(cells))
        self.ok()
        return {'vod_id': raw, 'vod_name': s._clean(data.get('title')),
                'vod_pic': data.get('poster_url') or '',
                'vod_year': str(data.get('year') or ''),
                'vod_area': s._clean(data.get('area') or ''),
                'vod_content': s._clean(data.get('description') or ''),
                'vod_remarks': s._clean(data.get('remarks') or ''),
                'vod_actor': ','.join((data.get('actors') or [])[:12]),
                'vod_director': ','.join((data.get('directors') or [])[:6]),
                'type_name': ','.join((data.get('genres') or [])[:4]),
                'vod_play_from': '$$$'.join(labels),
                'vod_play_url': '$$$'.join(bodies)}

    def play(self, flag, pid):
        return self.call(self.get().playerContent, flag, pid, {}) or {}


def _quote(s):
    try:
        from urllib.parse import quote
        return quote(str(s), safe='')
    except Exception:
        return str(s)


class XingGuang(Adapter):
    key = 'xg'
    supports = ('movie', 'tv', 'anime', 'variety', 'doc')
    filters = ('cls', 'area', 'year')
    TID = {'movie': 'movie', 'tv': 'tv', 'anime': 'anime', 'variety': 'show', 'doc': 'doc'}

    def _spawn(self):
        return _new_spider('xg', '')

    def ext_in(self, ext):
        out = {}
        m = {'cls': 'class', 'area': 'area', 'year': 'year'}
        for k, v in (ext or {}).items():
            if v and k in m:
                out[m[k]] = AREA_ALIAS.get(v, v) if k == 'area' else v
        by = {'new': 'created', 'score': 'score'}.get(str((ext or {}).get('sort') or ''))
        if by:
            out['by'] = by
        return out

    def _norm(self, v):
        return {'vod_id': str(v.get('vod_id') or ''),
                'vod_name': _fmt_remark(v.get('vod_name')),
                'vod_pic': v.get('vod_pic') or '',
                'vod_remarks': _fmt_remark(v.get('vod_remarks')),
                'vod_year': str(v.get('vod_year') or ''),
                'vod_score': str(v.get('vod_score') or v.get('score') or ''),
                'type_name': ''}

    def catalog(self, cls, page, ext):
        tid = self.TID.get(cls)
        if not tid:
            return []
        d = self.call(self.get().categoryContent, tid, page, None, self.ext_in(ext))
        self.ok()
        return [self._norm(v) for v in (d.get('list') or [])]

    def catalog_by_tid(self, tid, page, ext=None):
        d = self.call(self.get().categoryContent, str(tid), str(page), None, self.ext_in(ext))
        self.ok()
        return [self._norm(v) for v in (d.get('list') or [])]

    def hot(self, page):
        if page > 1:
            return self.catalog('movie', page, {})
        d = self.call(self.get().homeVideoContent)
        self.ok()
        return [self._norm(v) for v in (d.get('list') or [])]

    def search(self, key, page):
        d = self.call(self.get().searchContent, key, False, str(page))
        self.ok()
        return [self._norm(v) for v in (d.get('list') or [])]

    def detail(self, raw):
        d = self.call(self.get().detailContent, [raw])
        self.ok()
        lst = d.get('list') or []
        return lst[0] if lst else None

    def play(self, flag, pid):
        return self.call(self.get().playerContent, flag, pid, {}) or {}


class Pan(Adapter):
    key = 'wp'
    supports = ('movie', 'tv', 'variety', 'anime', 'doc', 'short')
    CATE = {'movie': '1', 'tv': '2', 'variety': '3', 'anime': '4', 'doc': '5', 'short': '26'}

    def _spawn(self):
        return _new_spider('wp', json.dumps({}))

    def _norm(self, v):
        return {'vod_id': str(v.get('vod_id') or ''),
                'vod_name': _fmt_remark(v.get('vod_name')),
                'vod_pic': v.get('vod_pic') or '',
                'vod_remarks': _fmt_remark(v.get('vod_remarks')),
                'vod_year': str(v.get('vod_year') or ''),
                'vod_score': str(v.get('vod_score') or v.get('score') or ''),
                'type_name': ''}

    def catalog(self, cls, page, ext):
        cate = self.CATE.get(cls)
        if not cate:
            return []
        sites = list(self.agg.opt['pan_sites'])
        tasks = []
        for sid in sites:
            tasks.append(((lambda s: lambda: self.call(self.get().categoryContent, s, page, None, {'cateId': cate}))(sid), (), sid))
        done = self.agg._parallel(tasks, float(self.agg.opt['wp_timeout']))
        got = dict(done)
        out = []
        for sid in sites:
            res = got.get(sid)
            if res:
                self.ok()
                out.extend([self._norm(v) for v in (res.get('list') or [])])
        return out

    def hot(self, page):
        if page > 1:
            return []
        return self.catalog('movie', 1, {})

    def search(self, key, page):
        ns = _load_src('wp')
        fn = ns.get('_site_search')
        out = []
        for sid in self.agg.opt['pan_sites']:
            site = self.get().sites.get(sid)
            if not site or not fn:
                continue
            try:
                vods = fn(site, key, str(page)) or []
            except Exception:
                vods = []
            for v in vods[:12]:
                v = dict(v)
                v['vod_id'] = '%s@%s' % (sid, v.get('vod_id'))
                out.append(self._norm(v))
            self.ok()
        return out

    def detail(self, raw):
        d = self.call(self.get().detailContent, [raw])
        self.ok()
        lst = d.get('list') or []
        return lst[0] if lst else None

    def play(self, flag, pid):
        return self.call(self.get().playerContent, flag, pid, None) or {}


class HongGuo(Adapter):
    key = 'hg'
    supports = ('short',)
    filters = ('cls', 'ch')

    def _spawn(self):
        return _new_spider('hg', '')

    def _norm(self, v):
        return {'vod_id': str(v.get('vod_id') or ''),
                'vod_name': _fmt_remark(v.get('vod_name')),
                'vod_pic': v.get('vod_pic') or '',
                'vod_remarks': _fmt_remark(v.get('vod_remarks')),
                'vod_year': str(v.get('vod_year') or ''),
                'vod_score': str(v.get('vod_score') or v.get('score') or ''),
                'type_name': '短剧'}

    @staticmethod
    def routes(ext):
        ch = str((ext or {}).get('ch') or '').strip()
        if ch in ('real-drama', 'comic-drama', 'ai-drama'):
            return [ch]
        return ['real-drama', 'comic-drama', 'ai-drama']

    def ext_in(self, ext):
        cat = HG_CAT.get(str((ext or {}).get('cls') or '').strip())
        return {'cat': cat} if cat else {}

    def catalog_route(self, route, page, ext):
        d = self.call(self.get().categoryContent, route, page, None, self.ext_in(ext))
        self.ok()
        return [self._norm(v) for v in (d.get('list') or [])]

    def catalog(self, cls, page, ext):
        return self.catalog_route(self.routes(ext)[0], page, ext)

    def hot(self, page):
        # 新版红果源没有 rank 频道，用真人剧频道当热榜
        for tid, ext in (('rank', {'cat': 'hot-drama'}), ('real-drama', {}), ('season', {})):
            try:
                d = self.call(self.get().categoryContent, tid, page, None, ext)
                lst = d.get('list') or []
                if lst:
                    self.ok()
                    return [self._norm(v) for v in lst]
            except Exception:
                continue
        return []

    def search(self, key, page):
        d = self.call(self.get().searchContent, key, False, str(page))
        self.ok()
        return [self._norm(v) for v in (d.get('list') or [])]

    def detail(self, raw):
        d = self.call(self.get().detailContent, [raw])
        self.ok()
        lst = d.get('list') or []
        return lst[0] if lst else None

    def play(self, flag, pid):
        return self.call(self.get().playerContent, flag, pid, None) or {}


class XinYun(Adapter):
    key = 'xy'
    supports = ('movie', 'tv', 'variety', 'anime', 'kids', 'doc')
    filters = ('cls', 'area', 'year')
    CN = {'movie': u'电影', 'tv': u'剧集', 'variety': u'综艺',
          'anime': u'动漫', 'kids': u'少儿', 'doc': u'纪录片'}

    def _norm(self, v):
        return {'vod_id': str(v.get('vod_id') or ''),
                'vod_name': _fmt_remark(v.get('vod_name')),
                'vod_pic': v.get('vod_pic') or '',
                'vod_remarks': _fmt_remark(v.get('vod_remarks')),
                'vod_year': str(v.get('vod_year') or ''),
                'vod_score': str(v.get('vod_score') or v.get('score') or ''),
                'type_name': v.get('type_name') or ''}

    def ext_in(self, ext):
        out = {}
        m = {'cls': 'cls', 'area': 'region', 'year': 'year'}
        for k, v in (ext or {}).items():
            if v and k in m:
                out[m[k]] = AREA_ALIAS.get(v, v) if k == 'area' else v
        st = {'hot': u'最热', 'new': u'最新', 'score': u'评分'}.get(str((ext or {}).get('sort') or ''))
        if st:
            out['sort'] = st
        return out

    def catalog(self, cls, page, ext):
        cn = self.CN.get(cls) or cls
        e = self.ext_in(ext)
        d = self.call(self.get().categoryContent, cn, str(page), None, e)
        self.ok()
        return [self._norm(v) for v in (d.get('list') or [])]

    def catalog_by_tid(self, tid, page, ext=None):
        e = self.ext_in(ext)
        d = self.call(self.get().categoryContent, tid, str(page), None, e)
        self.ok()
        return [self._norm(v) for v in (d.get('list') or [])]

    def hot(self, page):
        if page > 1:
            return self.catalog('movie', page, {})
        d = self.call(self.get().homeVideoContent)
        self.ok()
        return [self._norm(v) for v in (d.get('list') or [])]

    def search(self, key, page):
        d = self.call(self.get().searchContent, key, False, str(page))
        self.ok()
        return [self._norm(v) for v in (d.get('list') or [])]

    def detail(self, raw):
        d = self.call(self.get().detailContent, [raw])
        self.ok()
        lst = d.get('list') or []
        return lst[0] if lst else None

    def play(self, flag, pid):
        return self.call(self.get().playerContent, flag, pid, None) or {}


# =============================================================================
# 五、聚合 Spider
# =============================================================================
# 一级分类：只看内容形态。源不再单独占分类位——“来源”下沉成二级筛选，
# 这样一级只有 8 个，不会出现“影探·电影 / 搜剧·电影 / 红果·真人剧 …”二十多个并列。
LEVEL1 = [
    ('hot',     u'🔥 今日热榜'),
    ('movie',   u'🎬 电影'),
    ('tv',      u'📺 剧集'),
    ('anime',   u'🌸 动漫'),
    ('variety', u'🎤 综艺'),
    ('doc',     u'🌍 纪录片'),
    ('short',   u'⚡ 短剧'),
    ('kids',    u'🧸 少儿'),
]

# 二级“分类”（题材）：取各源词表并集。只有影探 / 星光 / 新云支持题材筛选，
# 一旦选了具体题材，只向这几家要数据，其余源不掺进来凑数。
GENRES = {
    'movie': [u'剧情', u'喜剧', u'爱情', u'动作', u'科幻', u'动画', u'悬疑', u'犯罪',
              u'惊悚', u'恐怖', u'冒险', u'奇幻', u'战争', u'武侠', u'古装', u'历史', u'家庭', u'灾难'],
    'tv': [u'剧情', u'爱情', u'古装', u'悬疑', u'犯罪', u'家庭', u'喜剧', u'战争', u'动作',
           u'奇幻', u'科幻', u'武侠', u'冒险', u'恐怖', u'历史', u'短片'],
    'anime': [u'热血', u'冒险', u'奇幻', u'科幻', u'爱情', u'喜剧', u'武侠', u'悬疑',
              u'惊悚', u'运动', u'历史', u'战争', u'动画', u'家庭', u'剧情'],
    'variety': [u'真人秀', u'音乐', u'脱口秀', u'综艺', u'美食', u'旅行'],
    'doc': [u'自然', u'美食', u'社会', u'人文', u'历史', u'军事', u'科技', u'财经',
            u'探险', u'罪案', u'竞技', u'旅游'],
    'kids': [u'看动画', u'玩玩具', u'听儿歌', u'看绘本', u'涨知识', u'学英语',
             u'识字拼音', u'好习惯', u'国学', u'做手工', u'冒险救援', u'生活日常', u'搞笑', u'动物', u'公主'],
}

AREAS = [u'中国大陆', u'中国香港', u'中国台湾', u'美国', u'日本', u'韩国',
         u'英国', u'泰国', u'其他']
# 各源认的是“大陆/香港/台湾”，这里统一翻译
AREA_ALIAS = {u'中国大陆': u'大陆', u'中国香港': u'香港', u'中国台湾': u'台湾'}
YEARS = [str(y) for y in range(2026, 2015, -1)]
# 排序：综合 / 热度 / 首映 / 高分（首映按年份倒序，高分按评分倒序，热度走各源原生热榜序）
SORTS = [('', u'综合'), ('hot', u'热度'), ('new', u'首映'), ('score', u'高分')]

# 短剧二级：红果官方四套频道 + 官方题材（题材值会翻成官方枚举）
HG_CHANNELS = [('real-drama', u'真人剧'), ('comic-drama', u'漫剧'), ('ai-drama', u'AI剧')]
HG_CAT = {
    u'爱情': 'romance', u'年代': 'period', u'逆袭': 'comeback', u'传奇': 'legend',
    u'成长': 'growth', u'家庭': 'family', u'家族': 'clan', u'萌宝': 'cute-kids',
    u'悬疑': 'suspense', u'惊悚': 'thriller', u'恐怖': 'horror', u'志怪': 'supernatural',
    u'古装': 'costume', u'玄幻': 'fantasy', u'奇幻': 'wonder', u'都市': 'urban',
    u'青春': 'youth', u'喜剧': 'comedy', u'科幻': 'sci-fi', u'灾难': 'disaster',
    u'动作冒险': 'action-adventure', u'战争': 'war', u'综艺': 'variety', u'剧情': 'drama',
    u'脑洞': 'creative', u'末世': 'apocalypse', u'豪门': 'wealthy-family', u'冒险': 'adventure',
}
SHORT_GENRES = [u'爱情', u'逆袭', u'悬疑', u'惊悚', u'恐怖',
                u'古装', u'年代', u'传奇', u'玄幻', u'奇幻', u'都市', u'青春', u'家庭',
                u'家族', u'萌宝', u'成长', u'喜剧', u'科幻', u'脑洞', u'末世', u'豪门',
                u'冒险', u'动作冒险', u'战争', u'剧情']

DEFAULTS = {
    'hide_sd': '1',
    'probe': '2',
    'probe_max': '9',
    'probe_budget': '6',
    'season_merge': '1',
    'sources': 'yt,sj,xg,wp,hg,xy',
    'pan_sites': '多多,木偶',
    'max_groups': '18',
    'hidden_groups': '8',
    'native_cats': '1',
    'unified_exclude': '',
    'list_timeout': '6',
    'wp_timeout': '20',
    'light_budget': '1.5',
    'solo_check_max': '3',
    'auto_quality': '1',
    'min_4k_mbps': '2.2',
    'detail_timeout': '18',
}


class Spider(_BaseSpider):
    def __init__(self):
        self.opt = dict(DEFAULTS)
        self.adapters = {}
        self.ready = False
        self._lock = threading.Lock()
        self._groups = {}
        self._group_file = None
        self._probe_cache = {}
        self._cat_cache = {}
        self._detail_cache = {}
        self._play_cache = {}
        self._page_seen = {}
        self._nat_cache = None
        self._yt_map = {}

    # ---------------------------------------------------------------- init
    def getName(self):
        return u'全站聚合'

    def init(self, extend=''):
        ext = {}
        if isinstance(extend, dict):
            ext = dict(extend)
        elif isinstance(extend, str) and extend.strip():
            try:
                ext = json.loads(extend)
            except Exception:
                ext = {}
        merged = dict(DEFAULTS)
        for k, v in (ext or {}).items():
            if v is None:
                continue
            merged[str(k)] = str(v)
        for k, v in ext.items():
            if str(k).endswith('_ext'):
                merged[str(k)] = v
        self.opt = merged
        keys = [x.strip() for x in str(self.opt.get('sources') or '').split(',') if x.strip()]
        sites = [x.strip() for x in str(self.opt.get('pan_sites') or '').split(',') if x.strip()]
        self.opt['pan_sites'] = sites or ['多多']
        makers = {'yt': YingTan, 'sj': Souju, 'xg': XingGuang, 'wp': Pan, 'hg': HongGuo, 'xy': XinYun}
        self.adapters = {}
        for k in SRC_ORDER:
            if k in keys and k in makers:
                self.adapters[k] = makers[k](self)
        self._load_groups()

    def _load_groups(self):
        try:
            path = os.path.join(tempfile.gettempdir(), 'tvbox_agg_groups.json')
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                now = time.time()
                for k, v in data.items():
                    if isinstance(v, dict) and now - float(v.get('ts') or 0) < 6 * 3600:
                        self._groups[k] = v
            self._group_file = path
        except Exception:
            self._group_file = None

    def _save_groups(self):
        if not self._group_file:
            return
        try:
            now = time.time()
            slim = {}
            for k, v in list(self._groups.items()):
                if now - float(v.get('ts') or 0) < 6 * 3600:
                    slim[k] = v
            with open(self._group_file, 'w', encoding='utf-8') as f:
                json.dump(slim, f, ensure_ascii=False)
        except Exception:
            pass

    # ------------------------------------------------------------ helpers
    def _listed(self):
        return [a for a in self.adapters.values() if a.alive()]

    def _parallel(self, tasks, timeout):
        """tasks: [(fn, args, tag)]；超时返回已完成的部分，顺序按 tag。"""
        if not tasks:
            return []
        pool = ThreadPoolExecutor(max_workers=max(1, len(tasks)))
        futs = {}
        for fn, args, tag in tasks:
            futs[pool.submit(fn, *args)] = tag
        done = []
        try:
            dw, _ = wait(list(futs.keys()), timeout=timeout)
            for f in dw:
                try:
                    done.append((futs[f], f.result()))
                except Exception:
                    done.append((futs[f], None))
        finally:
            pool.shutdown(wait=False)
        return done

    @staticmethod
    def _key(name, year=''):
        return _norm_title(name) + '|' + str(year or '')

    def _source_tag(self, key, item):
        return {'vod_id': '%s@%s' % (key, item['vod_id']),
                'vod_name': item['vod_name'],
                'vod_pic': item.get('vod_pic') or '',
                'vod_remarks': item.get('vod_remarks') or '',
                'vod_year': item.get('vod_year') or '',
                'vod_score': item.get('vod_score') or '',
                'type_name': item.get('type_name') or ''}

    def _dedupe(self, items):
        """同片名（同一年）只留一条，优先 4K/HDR，其次源优先级。"""
        out, seen = [], {}
        for it in items:
            key = self._key(it['vod_name'], it.get('vod_year'))
            if key not in seen:
                seen[key] = len(out)
                out.append(it)
                continue
            idx = seen[key]
            old = out[idx]
            def rank(x):
                r = str(x.get('vod_remarks') or '').upper()
                return (2 if '4K' in r else 1 if 'HDR' in r else 0,
                        -SRC_ORDER.index(x['vod_id'].split('@')[0]) if x['vod_id'].split('@')[0] in SRC_ORDER else -99)
            if rank(it) > rank(old):
                out[idx] = it
        return out

    def _interleave(self, buckets):
        out = []
        buckets = [list(b) for b in buckets if b]
        while buckets:
            rest = []
            for b in buckets:
                out.append(b.pop(0))
                if b:
                    rest.append(b)
            buckets = rest
        return out

    # ---------------------------------------------------------------- home
    def homeContent(self, filter):
        classes, filters, _yt = self._class_spec()
        return {'class': classes, 'filters': filters}

    def _class_spec(self):
        """多级分类规格。
        一级：内容形态（LEVEL1，8 个）；
        二级：filters（分类=题材 / 频道 / 地区 / 年份 / 来源 / 排序），同一套键名全站通用；
        三级：影片列表。
        """
        if getattr(self, '_nat_cache', None):
            return self._nat_cache
        keys = [a.key for a in self.adapters.values() if a.alive()]
        classes = [{'type_id': k, 'type_name': n} for k, n in LEVEL1]
        yt_groups, yt_map = [], {}

        yt = self.adapters.get('yt')
        if yt and 'yt' in keys:
            try:
                ycls = yt.get().homeContent(False)
                exact = {u'电影': 'movie', u'电视剧': 'tv', u'动漫': 'anime', u'综艺': 'variety',
                         u'短剧': 'short', u'记录片': 'doc', u'纪录片': 'doc', u'少儿动画': 'kids'}
                drop = set(['45', '54'])   # 明星专辑 / 无损音乐，不是影视分类
                cands = {}
                cur = None
                for c in (ycls.get('class') or []):
                    tid = str(c.get('type_id') or '').strip()
                    nm = str(c.get('type_name') or '').strip().replace(u'记录片', u'纪录片')
                    if tid in drop or not tid or not nm:
                        continue
                    if re.match(u'^[①②③④⑤⑥⑦⑧⑨⑩]$', nm) and cur is not None:
                        cur['tids'].append(tid)
                        continue
                    base = re.sub(u'[①②③④⑤⑥⑦⑧⑨⑩]$', '', nm).strip() or nm
                    cur = {'cid': tid, 'name': base, 'tids': [tid]}
                    yt_groups.append(cur)
                    cls = exact.get(base) or _yt_cls_of(base)
                    if cls:
                        # 精确名（电影/电视剧/动漫…）优先，其余同义词只做候选
                        cands.setdefault(cls, []).append((0 if base in exact else 1, tid))
                for cls, arr in cands.items():
                    arr.sort()
                    yt_map[cls] = [arr[0][1]]
            except Exception:
                yt_groups, yt_map = [], {}
        for cls, tid in (('movie', '47'), ('tv', '48'), ('anime', '49'), ('variety', '50'),
                         ('short', '22'), ('doc', '55'), ('kids', '29')):
            yt_map.setdefault(cls, [tid])      # 导航缺失时退回实测可用的总类 tid
        self._yt_map = yt_map

        filters = {}
        for k, _n in LEVEL1:
            if k == 'hot':
                continue
            groups = []
            # 第一排：综合 / 热度 / 首映 / 高分
            groups.append({'key': 'sort', 'name': u'排序', 'init': '',
                           'value': [{'n': n, 'v': v} for v, n in SORTS]})
            if k == 'short':
                groups.append({'key': 'cls', 'name': u'类型', 'init': '',
                               'value': [{'n': u'全部类型', 'v': ''}] +
                                        [{'n': g, 'v': g} for g in SHORT_GENRES]})
                groups.append({'key': 'ch', 'name': u'频道', 'init': '',
                               'value': [{'n': u'全部频道', 'v': ''}] +
                                        [{'n': n, 'v': v} for v, n in HG_CHANNELS]})
            else:
                groups.append({'key': 'cls', 'name': u'类型', 'init': '',
                               'value': [{'n': u'全部类型', 'v': ''}] +
                                        [{'n': g, 'v': g} for g in GENRES.get(k, [])]})
                groups.append({'key': 'area', 'name': u'地区', 'init': '',
                               'value': [{'n': u'全部地区', 'v': ''}] + [{'n': a, 'v': a} for a in AREAS]})
                groups.append({'key': 'year', 'name': u'年代', 'init': '',
                               'value': [{'n': u'全部年代', 'v': ''}] + [{'n': y, 'v': y} for y in YEARS]})
            srcs = [a for a in self.adapters.values() if a.key in keys and k in a.supports]
            if len(srcs) > 1:
                groups.append({'key': 'src', 'name': u'来源', 'init': '',
                               'value': [{'n': u'全部来源', 'v': ''}] +
                                        [{'n': SRC_NAME.get(a.key, a.key), 'v': a.key} for a in srcs]})
            filters[k] = groups

        self._nat_cache = (classes, filters, yt_groups)
        return self._nat_cache

    def homeVideoContent(self):
        return self.categoryContent('hot', '1', None, {})

    # ------------------------------------------------------------ category
    def categoryContent(self, tid, pg, filter, extend):
        tid = str(tid or '').strip()
        cache_key = None
        try:
            page = max(1, int(pg))
        except Exception:
            page = 1
        ext = extend if isinstance(extend, dict) else {}
        if isinstance(extend, str) and extend:
            try:
                ext = json.loads(extend)
            except Exception:
                ext = {}
        try:
            cache_key = (tid, page, json.dumps(ext or {}, sort_keys=True))
            hit = (self._cat_cache or {}).get(cache_key)
            if hit and time.time() < hit[0]:
                return hit[1]
        except Exception:
            cache_key = None
        if tid.startswith('hg~'):
            res = self._native_category(tid, page, ext)
            return self._cat_remember(cache_key, res)
        if tid.startswith('yt~'):
            return self._cat_remember(cache_key, self._yt_category(tid, page, ext))
        if tid.startswith('sj~'):
            return self._cat_remember(cache_key, self._sj_category(tid, page, ext))
        if tid.startswith('xy~'):
            return self._cat_remember(cache_key, self._native_category(tid, page, ext))
        if tid.startswith('wp~'):
            return self._cat_remember(cache_key, self._wp_category(tid, page, ext))
        want = str(ext.get('src') or '').strip()
        ex = [x.strip() for x in str(self.opt.get('unified_exclude') or '').split(',') if x.strip()]
        ad = [a for a in self.adapters.values()
              if a.alive() and a.key not in ex and (not want or a.key == want)]
        if tid == 'hot':
            return self._cat_remember(cache_key, self._hot(page, ad))
        tasks = []
        for a in self._filter_adapters(ad, tid, ext):
            if a.key == 'yt':
                for tt in (self._yt_map.get(tid) or []):
                    tasks.append(((lambda ad_, t: lambda: ad_.catalog_by_tid(t, page, ext))(a, tt),
                                  (), 'yt'))
            elif a.key == 'hg':
                for rt in HongGuo.routes(ext):
                    tasks.append(((lambda ad_, r: lambda: ad_.catalog_route(r, page, ext))(a, rt),
                                  (), 'hg'))
            else:
                tasks.append((a.catalog, (tid, page, ext), a.key))
        done = self._parallel(tasks, float(self.opt['list_timeout']))
        buckets = []
        for key, res in done:
            if res:
                buckets.append([self._source_tag(key, v) for v in res])
        items = self._dedupe(self._interleave(buckets))[:90]
        st = str(ext.get('sort') or '')
        if st == 'new':
            items.sort(key=lambda it: _year_int(it.get('vod_year')), reverse=True)
        elif st == 'score':
            items.sort(key=lambda it: _score_val(it.get('vod_score')), reverse=True)
        items = self._cross_page_filter('c:' + tid, page, items)
        for it in items:
            it['vod_remarks'] = self._remark_with_src(it)
        total = len(items)
        pagecount = 999 if items else page
        return self._cat_remember(cache_key, {'list': items, 'page': page, 'pagecount': pagecount,
                                              'limit': 90, 'total': max(total, 999999)})

    def _filter_adapters(self, ad, tid, ext):
        """二级筛选落到哪几家：选了某维度就只问支持该维度的源，不掺无用数据。"""
        need = [k for k in ('cls', 'area', 'year', 'ch') if str((ext or {}).get(k) or '').strip()]
        out = []
        for a in ad:
            if tid not in a.supports:
                continue
            if any(k not in a.filters for k in need):
                continue
            out.append(a)
        return out

    def _cat_remember(self, key, res):
        if key and isinstance(res, dict) and res.get('list'):
            try:
                if len(self._cat_cache) > 160:
                    self._cat_cache.clear()
                self._cat_cache[key] = (time.time() + 180, res)
            except Exception:
                pass
        return res

    def _native_category(self, tid, page, ext):
        key, cid = tid[:2], tid[3:]
        ad = self.adapters.get(key)
        if not ad:
            return {'list': [], 'page': page, 'pagecount': page, 'limit': 90, 'total': 0}
        try:
            d = ad.call(ad.get().categoryContent, cid, str(page), None, ext) or {}
            ad.ok()
        except Exception:
            return {'list': [], 'page': page, 'pagecount': page, 'limit': 90, 'total': 0}
        items = [self._source_tag(key, v) for v in (d.get('list') or [])]
        return self._native_result('n:%s:%s' % (key, cid), page, items)

    def _native_result(self, bucket, page, items):
        if page <= 1:
            self._page_seen[bucket] = set()
        seen = self._page_seen.setdefault(bucket, set())
        out = []
        for it in items:
            vid = it['vod_id']
            if vid in seen:
                continue
            seen.add(vid)
            out.append(it)
        return {'list': out, 'page': page, 'pagecount': 999 if out else page,
                'limit': 90, 'total': max(len(out), 999999)}

    def _yt_category(self, tid, page, ext):
        ad = self.adapters.get('yt')
        groups = (self._class_spec()[2] or [])
        g = None
        for x in groups:
            if 'yt~' + x['cid'] == tid:
                g = x
                break
        if not ad or not g:
            return {'list': [], 'page': page, 'pagecount': page, 'limit': 90, 'total': 0}
        e2 = ad.ext_in(dict((k, v) for k, v in (ext or {}).items() if k not in ('cat', 'src')))
        tasks = []
        for t in g['tids']:
            tasks.append(((lambda tt: lambda: ad.catalog_by_tid(tt, page, e2))(t), (), t))
        done = self._parallel(tasks, float(self.opt['list_timeout']))
        buckets = []
        for _t, res in done:
            if res:
                buckets.append([self._source_tag('yt', v) for v in res])
        items = self._dedupe(self._interleave(buckets))[:90]
        for it in items:
            it['vod_remarks'] = self._remark_with_src(it)
        return self._native_result('n:yt:%s' % g['cid'], page, items)

    def _sj_category(self, tid, page, ext):
        ad = self.adapters.get('sj')
        kind = tid[3:]
        if not ad:
            return {'list': [], 'page': page, 'pagecount': page, 'limit': 90, 'total': 0}
        try:
            d = ad.call(ad.get().categoryContent, 'kind:' + kind, str(page), None, ext or {}) or {}
            ad.ok()
        except Exception:
            return {'list': [], 'page': page, 'pagecount': page, 'limit': 90, 'total': 0}
        items = [self._source_tag('sj', v) for v in (d.get('list') or [])]
        return self._native_result('n:sj:' + kind, page, items)

    def _wp_category(self, tid, page, ext):
        cls = tid[3:]
        tasks = []
        if 'wp' in self.adapters:
            tasks.append((self.adapters['wp'].catalog, (cls, page, ext), 'wp'))
        if 'xg' in self.adapters and self.adapters['xg'].alive():
            tasks.append((self.adapters['xg'].catalog, (cls, page, ext), 'xg'))
        done = self._parallel(tasks, float(self.opt['wp_timeout']))
        buckets = []
        for k, res in done:
            if res:
                buckets.append([self._source_tag(k, v) for v in res])
        items = self._dedupe(self._interleave(buckets))[:90]
        for it in items:
            it['vod_remarks'] = self._remark_with_src(it)
        return self._native_result('n:wp:' + cls, page, items)

    def _hot(self, page, ad):
        """热榜按“每 4 排一类”轮询：电影 → 剧集 → 动漫 → 短剧，循环。"""
        ORDER = [('movie', u'电影'), ('tv', u'剧集'), ('anime', u'动漫'), ('short', u'短剧')]
        YT_TID = {'movie': '1', 'tv': '21', 'anime': '23', 'short': '22', 'variety': '24'}
        tasks = []
        avail = [a.key for a in ad]
        for cls, _nm in ORDER:
            a = self.adapters.get('yt')
            if a and a.alive() and 'yt' in avail:
                tasks.append(((lambda ad_, c: lambda: ad_.catalog_by_tid(YT_TID[c], page, {}))(a, cls), (), 'yt|' + cls))
            a = self.adapters.get('sj')
            if a and a.alive() and 'sj' in avail:
                tasks.append(((lambda ad_, c: lambda: ad_.catalog(c, page, {}))(a, cls), (), 'sj|' + cls))
            # 热榜不拉网盘站（单页 1–20s，太拖），网盘内容在“网盘·*”分类里看
        a = self.adapters.get('hg')
        if a and a.alive() and 'hg' in avail:
            tasks.append((a.hot, (page,), 'hg|short'))

        done = self._parallel(tasks, float(self.opt['wp_timeout']))
        pools = dict((c, []) for c, _n in ORDER)
        for tag, res in done:
            if not res:
                continue
            key, cls = tag.split('|')
            pool = pools.get(cls)
            if pool is None:
                continue
            for v in res:
                pool.append(self._source_tag(key, v))
        for cls, _nm in ORDER:
            pools[cls].sort(key=lambda it: SRC_ORDER.index(it['vod_id'].split('@')[0])
                            if it['vod_id'].split('@')[0] in SRC_ORDER else 99)

        # 每 4 排（12 条）换一个类别，按 电影→剧集→动漫→短剧 循环（热榜不放综艺）
        block = 12
        items = []
        seen = set()
        while len(items) < 90:
            moved = False
            for cls, _nm in ORDER:
                pool = pools[cls]
                take = 0
                while take < block and pool:
                    it = pool.pop(0)
                    k = self._key(it['vod_name'], it.get('vod_year'))
                    if k in seen:
                        continue
                    seen.add(k)
                    items.append(it)
                    take += 1
                    moved = True
                if len(items) >= 90:
                    break
            if not moved:
                break
        items = self._cross_page_filter('hot', page, items)
        for it in items:
            it['vod_remarks'] = self._remark_with_src(it)
        return {'list': items, 'page': page, 'pagecount': 999 if items else page,
                'limit': 90, 'total': max(len(items), 999999)}

    def _cross_page_filter(self, bucket, page, items):
        if page <= 1:
            self._page_seen[bucket] = set()
        seen = self._page_seen.setdefault(bucket, set())
        out = []
        for it in items:
            k = self._key(it['vod_name'], it.get('vod_year'))
            if k in seen:
                continue
            seen.add(k)
            out.append(it)
        return out

    @staticmethod
    def _remark_with_src(it):
        src = SRC_NAME.get(str(it['vod_id']).split('@')[0], '')
        r = str(it.get('vod_remarks') or '')
        if src and src not in r:
            r = (r + ' · ' + src).strip(' ·') if r else src
        return r

    # -------------------------------------------------------------- search
    def searchContent(self, key, quick, pg='1'):
        word = str(key or '').strip()
        try:
            page = max(1, int(pg))
        except Exception:
            page = 1
        if not word:
            return {'list': [], 'page': page, 'pagecount': 1}
        tasks = [(a.search, (word, page), a.key) for a in self.adapters.values() if a.alive()]
        done = self._parallel(tasks, float(self.opt['wp_timeout']))
        buckets = []
        for k, res in done:
            if res:
                buckets.append([self._source_tag(k, v) for v in res])
        items = self._dedupe(self._interleave(buckets))
        # 名称命中的排前面
        items.sort(key=lambda x: (0 if _norm_title(word) in _norm_title(x['vod_name']) else 1))
        items = items[:80]
        for it in items:
            it['vod_remarks'] = self._remark_with_src(it)
        return {'list': items, 'page': page, 'pagecount': 999 if items else page,
                'limit': 80, 'total': max(len(items), 999999)}

    # -------------------------------------------------------------- detail
    def detailContent(self, ids):
        if not ids:
            return {'list': []}
        vid = str(ids[0] if isinstance(ids, (list, tuple)) else ids)
        cache = self._detail_cache.get(vid)
        if cache and time.time() < cache[0]:
            return cache[1]
        res = self._detail_build([vid])
        if res.get('list'):
            self._detail_cache[vid] = (time.time() + 1800, res)
            # 首屏先给快照；缺画质标签的，后台深探升级（不阻塞、不清用户正看的缓存）
            if str(self.opt.get('probe')) == '1' and not getattr(self, '_bg_running', False):
                try:
                    vidkey = hashlib.md5(vid.encode('utf-8')).hexdigest()[:12]
                    payload = self._groups.get(vidkey) or {}
                    if any(not g.get('q') for g in (payload.get('groups') or [])):
                        self._bg_pending = getattr(self, '_bg_pending', set())
                        if vid not in self._bg_pending:
                            self._bg_pending.add(vid)
                            threading.Thread(target=self._bg_refresh_hg, args=(vid,), daemon=True).start()
                except Exception:
                    pass
        return res

    def _detail_build(self, ids):
        vid = str(ids[0] if isinstance(ids, (list, tuple)) else ids)

        key, raw = (vid.split('@', 1) + [''])[:2]
        ad = self.adapters.get(key)
        if not ad:
            # 没带源前缀：全局搜一次
            found = self.searchContent(raw or vid, False, '1').get('list') or []
            if not found:
                return {'list': []}
            vid = found[0]['vod_id']
            key, raw = vid.split('@', 1)
            ad = self.adapters.get(key)
            if not ad:
                return {'list': []}

        base = self._safe_detail(ad, raw)
        if not base:
            return {'list': [{'vod_id': vid, 'vod_name': raw, 'vod_pic': '',
                              'vod_content': '详情抓取失败，返回换一个结果',
                              'vod_play_from': '提示', 'vod_play_url': '换源重试$none'}]}

        name = base.get('vod_name') or ''
        bname, s_no, s_ok = split_season(name)
        groups = []

        self._append_groups(groups, key, base, bname, s_no)
        merge = str(self.opt['season_merge']) == '1'
        cand = []
        if merge:
            seasons_in_base = len(set(re.findall(u'第\\s*([0-9]{1,3}|[一二三四五六七八九十]{1,3})\\s*季',
                                              str(base.get('vod_play_from') or ''))))
            if not (key in ('hg', 'xy') and seasons_in_base >= 2 and not getattr(self, '_bg_full_mode', False)):
                cand = self._season_candidates(key, raw, bname, name, base, ad)
        if cand:
            tasks = [(self._safe_detail, (c[2], c[1]), (c[0], c[1])) for c in cand]
            done = self._parallel(tasks, max(4.0, float(self.opt['detail_timeout']) / 2))
            forces = dict(((c[0], c[1]), c[3]) for c in cand)
            for (k2, r2), d2 in done:
                if not d2:
                    continue
                n2 = d2.get('vod_name') or ''
                bn2, sn2, _ = split_season(n2)
                if title_match(bn2, bname):
                    self._append_groups(groups, k2, d2, bname, sn2, forces.get((k2, r2)))
        if not groups:
            return {'list': [dict(base, vod_id=vid, vod_play_from=base.get('vod_play_from') or '提示',
                                  vod_play_url=base.get('vod_play_url') or '暂无可用线路$none')]}

        groups = self._dedupe_groups(groups)
        self._probe_groups(groups)
        visible, hidden, chain = self._arrange(groups, bname)

        vidkey = hashlib.md5(vid.encode('utf-8')).hexdigest()[:12]
        payload = {'ts': time.time(), 'vid': vid, 'name': name, 'base': bname,
                   'groups': self._pack_groups(visible, hidden, chain),
                   'pool': self._pack_pool(hidden), 'vidkey': vidkey}
        self._groups[vidkey] = payload
        self._save_groups()

        froms, urls = [], []
        for label, eps in self._emit(payload['groups'], vidkey):
            froms.append(label)
            urls.append('#'.join('%s$%s' % (_clean_cell(t), tok) for t, tok in eps))

        show_name = bname if len(set(g['season'] for g in groups)) > 1 else name
        vod = {'vod_id': vid, 'vod_name': show_name,
               'vod_pic': base.get('vod_pic') or '',
               'vod_year': base.get('vod_year') or '',
               'vod_area': base.get('vod_area') or '',
               'vod_actor': base.get('vod_actor') or '',
               'vod_director': base.get('vod_director') or '',
               'type_name': base.get('type_name') or '',
               'vod_content': base.get('vod_content') or '',
               'vod_remarks': self._detail_remark(visible, show_name),
               'vod_play_from': '$$$'.join(froms),
               'vod_play_url': '$$$'.join(urls)}
        return {'list': [vod]}

    def _bg_refresh_hg(self, vid):
        self._bg_running = True
        self._bg_full_mode = True
        try:
            ns = _SRC_NS.get('hg') or {}
            for fn in ('_hg_seasons', '_hg_official_seasons_merged'):
                f = ns.get(fn)
                if f is not None and getattr(f, '__defaults__', None):
                    f.__defaults__ = (9.0,)
            # 清掉红果源自身的“截断分季”内存/磁盘缓存，否则补全还是拿旧结果
            try:
                sid = vid.split('@', 1)[1].replace('hg-series-v1:', '').strip()
                ns['_HG_SEASON_CACHE'].pop('season:' + sid, None)
                ns['_HG_SEASON_CACHE'].pop('sd:' + sid, None)
                disk = ns.get('_hg_disk_load') and ns['_hg_disk_load']()
                if isinstance(disk, dict):
                    disk.pop(sid, None)
                    if ns.get('_hg_disk_save'):
                        ns['_hg_disk_save'](disk)
            except Exception:
                pass
            old_probe = self.opt.get('probe')
            self.opt['probe'] = '2'          # 后台深探，标签升级成真实画质
            try:
                res = self._detail_build([vid])
                if res.get('list'):
                    self._detail_cache[vid] = (time.time() + 1800, res)
            finally:
                self.opt['probe'] = old_probe
        except Exception:
            pass
        finally:
            self._bg_running = False
            self._bg_full_mode = False
            try:
                for fn in ('_hg_seasons', '_hg_official_seasons_merged'):
                    f = (_SRC_NS.get('hg') or {}).get(fn)
                    if f is not None and getattr(f, '__defaults__', None):
                        f.__defaults__ = (2.5,)
            except Exception:
                pass

    def _safe_detail(self, ad, raw):
        try:
            return ad.detail(raw)
        except Exception:
            return None

    def _detail_remark(self, groups, name):
        seasons = set(g['season'] for g in groups)
        best = max([g.get('q') or {} for g in groups], key=lambda q: q.get('score') or 0, default={})
        bits = []
        if len(seasons) > 1:
            bits.append('全%d季' % len(seasons))
        bits.append(u'每季精选 %d 条' % len(groups))
        if best.get('label'):
            bits.append(best['label'])
        return ' · '.join(bits)

    def _season_candidates(self, key, raw, bname, name, base, ad):
        """同源兄弟季 + 影探/搜剧跨源同名条目（其它源优先占位，避免同源刷屏）。"""
        cap = 8
        out, seen = [], set([(key, raw)])
        if key == 'sj':
            try:
                for no, sid, _t in list(ad.seasons(raw))[:6]:
                    if (key, sid) not in seen:
                        seen.add((key, sid))
                        out.append((key, sid, ad, no))
            except Exception:
                pass
        if key in ('hg', 'yt', 'xy'):
            # 红果 / 影探 走“专属线路”：只补本源的兄弟季，不掺其它源
            look = [key]
        else:
            others = [k for k in ('yt', 'sj') if k != key]
            look = others + [key]
        tasks = []
        for k in look:
            a = self.adapters.get(k)
            if a and a.alive():
                tasks.append((a.search, (bname, 1), k))
        done = self._parallel(tasks, 2.5)
        resmap = dict(done)
        for k in look:
            res = resmap.get(k)
            a = self.adapters.get(k)
            if not a or not res:
                continue
            quota = len(out) + (4 if k != key else cap)
            for v in (res or [])[:12]:
                nm = v.get('vod_name') or ''
                bn2, sn2, _ = split_season(nm)
                if not title_match(bn2, bname):
                    continue
                if (k, v['vod_id']) in seen:
                    continue
                seen.add((k, v['vod_id']))
                out.append((k, str(v['vod_id']), a, None))
                if k == 'sj':
                    try:
                        for no, sid, _t in list(a.seasons(str(v['vod_id']))) [:3]:
                            if (k, sid) not in seen and len(out) < cap:
                                seen.add((k, sid))
                                out.append((k, sid, a, no))
                    except Exception:
                        pass
                if len(out) >= min(quota, cap):
                    break
            if len(out) >= cap:
                break
        return out

    def _append_groups(self, groups, key, det, bname, dflt_season, force=None):
        froms = str(det.get('vod_play_from') or '').split('$$$')
        urls = str(det.get('vod_play_url') or '').split('$$$')
        name = det.get('vod_name') or ''
        if force:
            dflt_season = int(force)
        for i, flag in enumerate(froms):
            if i >= len(urls) or not str(flag).strip():
                continue
            body = urls[i]
            if not body:
                continue
            sn = dflt_season
            m = re.search(r'第\s*([0-9]{1,3}|[一二三四五六七八九十]{1,3})\s*季', str(flag))
            if m:
                sn = _cn_int(m.group(1)) or dflt_season
            if u'全季连播' in str(flag):
                continue
            eps = []
            for cell in str(body).split('#'):
                if '$' in cell:
                    t, pid = cell.split('$', 1)
                else:
                    t, pid = '', cell
                if str(pid).strip() and str(pid).strip() != 'none':
                    eps.append((str(t).strip() or ('第%d集' % (len(eps) + 1)), str(pid).strip()))
            if not eps:
                continue

            def add(season_no, cells, prov):
                same = [g for g in groups if g['src'] == key and g['provider'] == prov
                        and g['season'] == int(season_no)]
                prov2 = '%s%d' % (prov if prov != '默认' else '线路', len(same) + 1) if same else prov
                groups.append({'src': key, 'flag': str(flag).strip(), 'provider': prov2,
                               'season': int(season_no or 1), 'eps': cells, 'title': name,
                               'q': None, 'reason': ''})

            prov = slim_provider(flag)
            if prov == u'新云帧享':
                prov = u'帧享'
            # 一条线路里塞了多季（如影探 43 集跨 S01-S05）：按集标题的 SxxE / 第N季 切开
            epmap = {}
            matched = 0
            for t, p2 in eps:
                no = ep_season(t)
                if no:
                    matched += 1
                    epmap.setdefault(no, []).append((t, p2))
            if len(epmap) >= 2 and matched >= max(2, int(len(eps) * 0.8)):
                for no in sorted(epmap):
                    add(no, epmap[no], prov)
                continue
            add(sn or 1, eps, prov)

    @staticmethod
    def _dedupe_groups(groups):
        out, seen = [], {}
        for g in groups:
            k = (g['src'], g['provider'], g['season'], len(g['eps']), g['eps'][0][1][:24])
            if k in seen:
                if len(g['eps']) > len(out[seen[k]]['eps']):
                    out[seen[k]] = g
                continue
            seen[k] = len(out)
            out.append(g)
        return out

    def _probe_groups(self, groups):
        mode = str(self.opt['probe'])
        if mode == '0' or not groups:
            return
        try:
            budget = float(self.opt['probe_budget'])
        except Exception:
            budget = 5.0
        buckets = {}
        for g in groups:
            buckets.setdefault(g['season'], []).append(g)

        if mode != '2':
            # 快速模式（默认）：不解析文件头，每季只按名字提示排序，实测确认首选线路能出地址。
            # 季数很多（如 13 季）时跳过校验，直接返回，靠播放时的回落兜底——这是秒开的关键。
            try:
                max_solo = int(self.opt.get('solo_check_max') or 4)
            except Exception:
                max_solo = 4
            if len(buckets) > max_solo:
                return
            picks = []
            for sn in sorted(buckets):
                sg = sorted(buckets[sn], key=lambda g: (self._hint_score(g), len(g['eps'])), reverse=True)
                if not sg:
                    continue
                if sg[0].get('src') in ('xy', 'hg'):
                    continue      # 这两个源直链稳定、播放自带回落，首屏不再花 1–2s 校验
                picks.append((sg, 0))

            def light(pick):
                sg, i = pick
                g = sg[i]
                ad = self.adapters.get(g['src'])
                if not ad:
                    return g, 'no-adapter'
                try:
                    res = ad.play(g['flag'], g['eps'][0][1]) or {}
                    url = str(res.get('url') or '')
                    if url:
                        g['url0'] = url
                        g['header0'] = res.get('header') or {}
                        try:
                            info = probe_quick(url, g['flag'] + ' ' + g['eps'][0][0], res.get('header'))
                            if info:
                                g['q'] = info
                        except Exception:
                            pass
                        return g, ''
                except Exception as e:
                    return g, type(e).__name__
                return g, 'play-empty'

            done = self._parallel([(light, (p,), p[0][0]['season']) for p in picks],
                                  min(budget, float(self.opt.get('light_budget') or 1.5)))
            bad = []
            for _tag, res in done:
                if not res:
                    continue
                g, why = res
                if why:
                    g['reason'] = why
                    bad.append(g['season'])
            # 首选失败：同季换下一条各试一次（最多 2 条）
            retry = [(buckets[sn], 1) for sn in bad
                     if len(buckets[sn]) > 1]
            if retry:
                done2 = self._parallel([(light, (p,), p[0][1]['season']) for p in retry], 3.0)
                for _tag, res in done2:
                    if res and not res[1]:
                        res[0].pop('reason', None)
            return

        # 深度模式：解析文件头拿真实 4K/HDR/声道
        #   probe=2 每季只探“名字提示最好”的那一条（够出标签，又比全排快）
        #   probe=3 每季最多三条全排（最准，最慢）
        try:
            pmax = int(self.opt['probe_max'])
        except Exception:
            pmax = 9
        solo, per = [], []
        for sn in sorted(buckets):
            sg = sorted(buckets[sn], key=lambda g: (self._hint_score(g), len(g['eps'])), reverse=True)
            if len(sg) == 1 or mode == '2':
                if sg:
                    solo.append(sg[0])
                continue
            per.append(sg[:3])
        cands = []
        if mode != '2':
            while len(cands) < pmax and any(per):
                for b in per:
                    if b and len(cands) < pmax:
                        cands.append(b.pop(0))

        def one(g):
            ad = self.adapters.get(g['src'])
            if not ad:
                return g, None, 'no-adapter'
            why = ''
            for attempt in (0, 1):
                try:
                    res = ad.play(g['flag'], g['eps'][0][1]) or {}
                    url = str(res.get('url') or '')
                    if not url:
                        why = 'play-empty'
                        continue
                    info = self._fast_url_label(url) or self._probe_url_cached(url, res.get('header'), g)
                    g['url0'] = url
                    g['header0'] = res.get('header') or {}
                    try:
                        g['mbps'] = speed_mbps(url, res.get('header'))
                    except Exception:
                        g['mbps'] = 0
                    if info:
                        return g, info, ''
                    why = 'probe-empty'
                except Exception as e:
                    why = type(e).__name__
            return g, None, why

        def light(g):
            ad = self.adapters.get(g['src'])
            if not ad:
                return g, None, 'no-adapter'
            try:
                res = ad.play(g['flag'], g['eps'][0][1]) or {}
                url = str(res.get('url') or '')
                if url:
                    g['url0'] = url
                    g['header0'] = res.get('header') or {}
                    return g, None, ''
            except Exception as e:
                return g, None, type(e).__name__
            return g, None, 'play-empty'

        done = self._parallel([(one, (g,), id(g)) for g in cands], budget)
        done += self._parallel([(one, (g,), id(g)) for g in solo], budget)
        for _tag, res in done:
            if not res:
                continue
            g, info, why = res
            if info:
                g['q'] = info
            else:
                g['reason'] = why
                g['q'] = {'score': 0, 'tags': [], 'label': ''}

    def _hint_score(self, g):
        f = (g['flag'] + ' ' + g['provider']).upper()
        s = 0
        if '4K' in f or '2160' in f:
            s += 40
        if 'HDR' in f or '杜比' in f or 'DV' in f:
            s += 20
        if '1080' in f:
            s += 10
        if '蓝光' in f or '原画' in f or 'REMUX' in f:
            s += 15
        return s

    @staticmethod
    def _fast_url_label(url):
        """红果自带代理地址里直接写了清晰度（q=1080/720…），不用再拉文件头。"""
        try:
            u = str(url or '')
            if 'hg.mp4' in u or '127.0.0.1:10010' in u:
                m = re.search(r'[?&]q=([0-9]{3,4})', u)
                if m:
                    h = int(m.group(1))
                    if h >= 2160:
                        return {'score': 3400, 'tags': ['4K'], 'label': '4K'}
                    if h >= 1080:
                        return {'score': 1200, 'tags': ['1080P'], 'label': '1080P'}
                    if h >= 720:
                        return {'score': 800, 'tags': ['720P'], 'label': '720P'}
                    return {'score': 600, 'tags': ['%dP' % h], 'label': '%dP' % h}
        except Exception:
            pass
        return None

    def _probe_url_cached(self, url, header, g):
        now = time.time()
        hit = self._probe_cache.get(url)
        if hit and now < hit[0]:
            return hit[1]
        info = probe_item(url, g['flag'] + ' ' + g['eps'][0][0], header)
        self._probe_cache[url] = (now + 6 * 3600, info)
        return info

    def _arrange(self, groups, bname):
        by_season = {}
        for g in groups:
            by_season.setdefault(g['season'], []).append(g)
        visible, pool = [], []
        for sn in sorted(by_season):
            sg = by_season[sn]
            best = self._choose_one(sg)
            if best:
                visible.append(best)
            pool += [g for g in sg if g is not best]
        try:
            hcap = int(self.opt.get('hidden_groups') or 8)
        except Exception:
            hcap = 8
        chain = None
        if len(by_season) > 1:
            chain = self._build_chain(visible, bname)
        return visible, pool[:hcap], chain

    def _choose_one(self, sg):
        """每季只留一条：先实测确认能播，再按画质、集数完整度排序。"""
        def score(g):
            return int((g.get('q') or {}).get('score', 0) or 0)
        def tier(g):
            sc = score(g)
            if sc >= 2900:
                return 0
            if sc >= 1000:
                return 1
            if sc > 0:
                return 2
            if not g.get('reason'):
                return 3
            return 4
        try:
            min4k = float(self.opt.get('min_4k_mbps') or 2.2)
        except Exception:
            min4k = 2.2
        auto = str(self.opt.get('auto_quality') or '1') == '1'
        if auto:
            best4k = None
            alt = None
            for g in sg:
                mb = float(g.get('mbps') or 0)
                is4k = score(g) >= 2900
                if is4k:
                    if best4k is None or mb > float(best4k.get('mbps') or 0):
                        best4k = g
                elif mb >= 1.0:
                    if alt is None or mb > float(alt.get('mbps') or 0):
                        alt = g
            if best4k and alt is not None and float(best4k.get('mbps') or 0) < min4k:
                return alt
        return sorted(sg, key=lambda g: (tier(g), -score(g),
                                         -float(g.get('mbps') or 0), len(g['eps']),
                                         self._hint_score(g)))[0]

    @staticmethod
    def _pick_diverse(items, n):
        buckets = {}
        for g in items:
            buckets.setdefault(g['src'], []).append(g)
        out = []
        while len(out) < n and any(buckets.values()):
            for k in list(buckets):
                if buckets[k] and len(out) < n:
                    out.append(buckets[k].pop(0))
        return out

    def _build_chain(self, groups, bname):
        seasons = sorted(set(g['season'] for g in groups))
        if len(seasons) < 2:
            return None
        chosen = []
        for sn in seasons:
            cand = [g for g in groups if g['season'] == sn]
            if not cand:
                continue
            chosen.append(sorted(cand, key=lambda g: -(int((g.get('q') or {}).get('score', 0) or 0)))[0])
        if len(chosen) < 2:
            return None
        eps = []
        for g in chosen:
            for i, (t, pid) in enumerate(g['eps']):
                eps.append([_chain_ep_label(t, g['season'], i + 1), g['src'], g['flag'], pid,
                            g['season'], i])
        return {'src': 'chain', 'flag': '全季连播', 'provider': '全季连播',
                'season': 0, 'eps': eps, 'title': bname}

    def _pack_groups(self, visible, pool, chain):
        out = []
        if chain:
            out.append({'src': 'chain', 'flag': '全季连播', 'provider': '全季连播',
                        'season': 0, 'chain': True,
                        'eps': [[e[0], e[1], e[2], e[3]] + list(e[4:]) for e in chain['eps']],
                        'n': len(chain['eps'])})
        for g in visible:
            out.append({'src': g['src'], 'flag': g['flag'], 'provider': g['provider'],
                        'season': g['season'], 'eps': [[t, p] for t, p in g['eps']],
                        'q': (g.get('q') or {}).get('label', ''),
                        'mbps': g.get('mbps') or 0})
        return out

    @staticmethod
    def _pack_pool(pool):
        out = []
        for g in pool:
            out.append({'src': g['src'], 'flag': g['flag'], 'provider': g['provider'],
                        'season': g['season'], 'eps': [[t, p] for t, p in g['eps']],
                        'mbps': g.get('mbps') or 0})
        return out

    def _emit(self, packed, vidkey):
        out = []
        base = (self._groups.get(vidkey) or {}).get('base') or ''
        for gi, g in enumerate(packed):
            season = cn_season(g.get('season') or 1)
            if g.get('chain'):
                label = u'全季连播 %d集' % (g.get('n') or len(g.get('eps') or []))
                eps = [(e[0], 'agg|%s|%d|%d' % (vidkey, gi, ei))
                       for ei, e in enumerate(g.get('eps') or [])]
                out.append((label, eps))
                continue
            label = u'%s-%s-%s《%s》' % (SRC_NAME.get(g['src'], g['src']),
                                        g.get('provider') or u'默认', season, base)
            if g.get('q'):
                tag = str(g['q'])
                if g.get('mbps') and 'MB/s' not in tag:
                    tag += u'·%.1fMB/s' % float(g['mbps'])
                label += u'[' + tag + u']'
            eps = [(e[0], 'agg|%s|%d|%d' % (vidkey, gi, ei))
                   for ei, e in enumerate(g.get('eps') or [])]
            out.append((label, eps))
        return out


def _chain_ep_label(title, season, idx):
    """全季连播的集名：前面加季数，如 第1季-1集 / 第2季-10集 / 第1季-大结局。"""
    raw = str(title or '').strip()
    m = re.match(u'^第?\\s*([0-9]{1,4})\\s*集?$', raw)
    body = ''
    if m:
        body = '%s集' % m.group(1)
    else:
        m2 = re.search(r'S\d+E(\d+)', raw, re.I)
        if m2:
            body = '%d集' % int(m2.group(1))
        m3 = re.search(u'第\\s*([0-9]{1,4})\\s*集', raw)
        if m3:
            body = '%s集' % m3.group(1)
    if not body:
        body = raw
    if not body:
        body = '%d集' % idx
    return u'第%d季-%s' % (int(season or 1), body)


def _chain_title(vidkey, store):
    try:
        return (store.get(vidkey) or {}).get('base') or u''
    except Exception:
        return u''


def _clean_cell(t):
    return re.sub(r'[$#]', ' ', str(t or '')).strip()


# =============================================================================
# 六、播放与回退
# =============================================================================
def _player(self, flag, pid, vipFlags=None):
    token = str(pid or '').strip()
    if token.startswith('agg|'):
        parts = token.split('|')
        if len(parts) < 3:
            return {'parse': 0, 'url': '', 'msg': 'bad token'}
        vidkey = parts[1]
        try:
            gi = int(parts[2] or 0)
            ei = int(parts[3] or 0) if len(parts) > 3 else 0
        except Exception:
            gi, ei = 0, 0
        payload = self._groups.get(vidkey)
        if not payload:
            return {'parse': 0, 'url': '', 'msg': '线路缓存已过期，请重新打开详情再播'}
        groups = payload.get('groups') or []
        if gi >= len(groups):
            return {'parse': 0, 'url': '', 'msg': '线路不存在'}
        g = groups[gi]
        pool = payload.get('pool') or []
        row = _play_group(self, g, ei)
        if row:
            return row
        # 4K 线路失效：同季隐藏线路按同一集号顶上
        if g.get('chain'):
            eps = g.get('eps') or []
            if eps:
                e = eps[min(ei, len(eps) - 1)]
                if len(e) >= 6:
                    for alt in groups:
                        if alt.get('chain') or alt.get('season') != e[4]:
                            continue
                        row = _play_group(self, alt, int(e[5]))
                        if row:
                            return row
        alts = [a for a in list(groups) + list(pool) if a is not g and not a.get('chain')]
        # 换线路：每 3 条并发试，谁先出地址就用谁，避免一条一条串行等
        for i in range(0, len(alts), 3):
            chunk = alts[i:i + 3]
            tasks = [((lambda x: lambda: _play_group(self, x, ei))(a), (), j)
                     for j, a in enumerate(chunk)]
            for _t, row in self._parallel(tasks, 8.0):
                if row:
                    return row
        return {'parse': 0, 'url': '', 'msg': '该集所有线路都无法播放'}
    if token.startswith('http'):
        return {'parse': 0, 'url': token, 'header': {}}
    return {'parse': 0, 'url': '', 'msg': '未知播放标识'}


def _play_group(self, g, ei):
    eps = g.get('eps') or []
    if not eps:
        return None
    if g.get('chain'):
        if ei >= len(eps):
            ei = max(0, len(eps) - 1)
        row = eps[ei]
        if len(row) >= 4:
            ad = self.adapters.get(row[1])
            if not ad:
                return None
            try:
                res = ad.play(row[2], row[3]) or {}
            except Exception:
                return None
            url = str(res.get('url') or '')
            if not url:
                return None
            return {'parse': int(res.get('parse') or 0), 'url': url,
                    'header': res.get('header') or {}}
        return None
    ad = self.adapters.get(g.get('src'))
    if not ad:
        return None
    if ei >= len(eps):
        ei = max(0, len(eps) - 1)
    title, pid = eps[ei]
    if str(pid).startswith('agg|'):
        return _player(self, 'chain', pid, None)
    ck = (g.get('src'), str(g.get('flag')), str(pid))
    hit = (self._play_cache or {}).get(ck)
    if hit and time.time() < hit[0]:
        return {'parse': int(hit[1].get('parse') or 0), 'url': hit[1].get('url') or '',
                'header': hit[1].get('header') or {}}
    try:
        res = ad.play(g.get('flag'), pid) or {}
    except Exception:
        return None
    url = str(res.get('url') or '')
    if not url:
        return None
    row = {'parse': int(res.get('parse') or 0), 'url': url, 'header': res.get('header') or {}}
    try:
        if len(self._play_cache) > 300:
            self._play_cache.clear()
        self._play_cache[ck] = (time.time() + 600, row)
    except Exception:
        pass
    return row


def _is_video(self, url):
    u = str(url or '').lower()
    return bool(re.search(r'\.(m3u8|mp4|mkv|ts|flv|avi|m4v|mov|webm)(\?|$)', u))


def _destroy(self):
    for a in list(self.adapters.values()):
        try:
            if a.s is not None and hasattr(a.s, 'destroy'):
                a.s.destroy()
        except Exception:
            pass
    self._groups = {}


def _local_proxy(self, param):
    return None


def _manual_check(self):
    return False


Spider.playerContent = _player
Spider.isVideoFormat = _is_video
Spider.manualVideoCheck = _manual_check
Spider.destroy = _destroy
Spider.localProxy = _local_proxy


# =============================================================================
# 七、自检（可选，在 PC 上 python 全站聚合.py 跑）
# =============================================================================
def _selftest():
    sp = Spider()
    sp.init('{}')
    print('name:', sp.getName())
    classes = sp.homeContent(True)
    print('classes:', [c['type_name'] for c in classes['class']])
    for k, groups in (classes.get('filters') or {}).items():
        print(' filters[%s]:' % k, [(g['name'], len(g['value'])) for g in groups])
    hot = sp.homeVideoContent()
    print('hot:', len(hot['list']), hot['list'][0]['vod_name'] if hot['list'] else '-')
    for cls in ('movie', 'tv', 'anime'):
        r = sp.categoryContent(cls, '1', None, {})
        print(cls, 'p1:', len(r['list']), r['list'][0]['vod_name'] if r['list'] else '-')
        r2 = sp.categoryContent(cls, '2', None, {})
        print(cls, 'p2:', len(r2['list']), r2['list'][0]['vod_name'] if r2['list'] else '-')
    s = sp.searchContent('危机边缘', False, '1')
    print('search:', len(s['list']), [x['vod_name'] for x in s['list'][:3]])
    if s['list']:
        d = sp.detailContent([s['list'][0]['vod_id']])
        v = d['list'][0]
        print('detail:', v['vod_name'], '|', v['vod_remarks'])
        print('froms:', v['vod_play_from'][:300])
        print('urls len:', [len(x.split('#')) for x in v['vod_play_url'].split('$$$')][:6])


if __name__ == '__main__':
    _selftest()
