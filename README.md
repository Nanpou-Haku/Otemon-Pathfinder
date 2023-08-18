Otemon Pathfinder
====
このレポジトリには、WRO Japan 2023 FUTURE ENGINEERSの自動運転車に関するエンジニアリング資料(すべてのコードや資料など)が含まれています。
___

## 目次

* [自己紹介](#%E8%87%AA%E5%B7%B1%E7%B4%B9%E4%BB%8B)
* [ロボットについて](#%E3%83%AD%E3%83%9C%E3%83%83%E3%83%88%E3%81%AB%E3%81%A4%E3%81%84%E3%81%A6)
* [ハードウェア](#%E3%83%8F%E3%83%BC%E3%83%89%E3%82%A6%E3%82%A7%E3%82%A2)
    * [写真](#%E3%83%AD%E3%83%9C%E3%83%83%E3%83%88%E3%81%AE%E5%86%99%E7%9C%9F)
    * [設計図](#%E8%A8%AD%E8%A8%88%E5%9B%B3)
      * 回路図
      * 構図
      * ステアリング部分
    * [構成の理由](#%E3%81%93%E3%81%AE%E6%A7%8B%E6%88%90%E3%81%AE%E7%90%86%E7%94%B1)
* [ソフトウェア](#%E3%82%BD%E3%83%95%E3%83%88%E3%82%A6%E3%82%A7%E3%82%A2)
  * [使用OS](#%E4%BD%BF%E7%94%A8OS)
  * [プログラミング言語](#%E3%83%97%E3%83%AD%E3%82%B0%E3%83%A9%E3%83%9F%E3%83%B3%E3%82%B0%E8%A8%80%E8%AA%9E)
  * [アルゴリズム](#%E3%82%A2%E3%83%AB%E3%82%B4%E3%83%AA%E3%82%BA%E3%83%A0)
    * [前提](#%E5%89%8D%E6%8F%90%0D%0A)
    * [Open Challenge](#OpenChallenge)
    * [Obstacle Challenge](#ObstacleChallenge)

## 自己紹介

私たちは「Otemon Pathfinder」です。私たちのチームには3人のメンバーがいます。

- 安井　昌望
- 南方　博
- 藤村　昭允
  
（左から）

![team_funny](https://github.com/washiwashiwashi/assignment/blob/images/img/team_funny.jpg)

## ロボットについて

私たちのロボットは車体をレゴのパーツで作っており、レゴのパーツで実現することができないものは3Dプリンターで部品を作り、レゴのパーツと互換性を持たせています。

![robot](https://github.com/washiwashiwashi/assignment/blob/images/img/robot.jpeg)

## ハードウェア

| デバイス |  | 用途 |
| :--: | :--:| :--: |
| Raspberry Pi 4B | <img src="https://github.com/washiwashiwashi/assignment/blob/images/img/remove%20background/raspberrypi4b-removebg-preview.png" width="100px"> | プログラムの実行およびその処理 |
| BuildHat | <img src="https://github.com/washiwashiwashi/assignment/blob/images/img/remove%20background/buildhat-removebg-preview.png" width="100px">| LEGOのモーターと接続し、Raspberry Piで制御 |
| Pi Camera V2 | <img src="https://github.com/washiwashiwashi/assignment/blob/images/img/remove%20background/Pi_camera_V2-removebg-preview.png" width="100px"> | 障害物認識、壁検知 |
| HC-SR04 | <img src="https://github.com/washiwashiwashi/assignment/blob/images/img/remove%20background/HC-SR04-removebg-preview.png" width="100px"> | 超音波センサーは壁との距離を計測 前面:衝突を回避 側面:時計回り・半時計回りの判別 |
| Large Angular Motor |　<img src="https://github.com/washiwashiwashi/assignment/blob/images/img/l_motor.png" width="100px"> | 駆動 |
| Medium Angular Motor | <img src="https://github.com/washiwashiwashi/assignment/blob/images/img/m_motor.png" width="100px"> | 操舵 |
| 18650(3.6V, 2600mAh) | <img src="https://github.com/washiwashiwashi/assignment/blob/images/img/remove%20background/18650-removebg-preview.png" width="100px"> | 電源供給 |
| Switch | <img src="https://github.com/washiwashiwashi/assignment/blob/images/img/remove%20background/switch-removebg-preview.png" width="100px"> | ロボットの起動 |

### ロボットの写真

| Front | Back |
| -- | -- |
| ![robot_front](https://github.com/washiwashiwashi/assignment/blob/images/img/robot_front.jpg) | ![robot_back](https://github.com/washiwashiwashi/assignment/blob/images/img/robot_back.jpg) |

| Left | Right |
| -- | -- |
| ![robot_left](https://github.com/washiwashiwashi/assignment/blob/images/img/robot_left.jpg) | ![robot_right](https://github.com/washiwashiwashi/assignment/blob/images/img/robot_right.jpg) |

| Top | Bottom |
| -- | -- |
| ![robot_top](https://github.com/washiwashiwashi/assignment/blob/images/img/robot_top.jpg) | ![robot_bottom](https://github.com/washiwashiwashi/assignment/blob/images/img/robot_bottom.jpg) |

### 設計図
* **回路図**

![diagram](https://github.com/washiwashiwashi/assignment/blob/images/img/scheme/wro2023-fe.png)

* **構図**

![blueprint](https://github.com/washiwashiwashi/assignment/blob/images/img/robot_blueprint.png)

ディファレンシャルギアはただモーターからタイヤに動力を伝えるのではなく、モーターからリングギアを通して、ピニオンギアやサイドギアへ繋ぎ、タイヤに動力を伝えています。こうすることで、タイヤが両方とも何の負荷もかからずに走行した場合はリングギアが回転し、ピニオンギアは動きません。しかし、どちらか片方が動かない、もしくは負荷がかかった場合にはピニオンギアが作動し、もう片方のタイヤを余分に回転させます。こうすることで**タイヤの回転差を調整し、スムーズな走行が可能**になり、コートでカーブする際に効果を発揮します。

![differential gear](https://github.com/washiwashiwashi/assignment/blob/images/img/gear.jpg) 

（ディファレンシャルギア）

* **ステアリング部分**

![steering](https://github.com/washiwashiwashi/assignment/blob/images/img/robot_steering.png)

### この構成の理由

1. トライ＆エラーのしやすさ：私たちはRaspberry Piの高い拡張性を活用することで、様々な種類のカメラモジュール、I2C接続センサー、GPIO制御を試しました。こうした豊富な選択肢を通じて、異なる手法やアプローチを試行し、最適解を求めていくことを可能にしました。

2. 最適な互換性：LEGOを選んだ理由は、**組み立てが容易で、ロボットの修理や新しい機構の追加が素早く行える**ためです。加えて、多様なパーツが利用でき、アイデアを迅速に形にできます。さらに、Raspberry Pi BuildHatを使用してLEGO SpikeのモーターをRaspberry Piで制御できる**高い互換性**があり、3Dプリンターを活用してLEGOと互換性のあるカスタムパーツを製作できるため、理想のロボットを作り上げるための自由度が高めました。

3. エネルギー効率とコスト：Lidarセンサーの代わりにカメラや超音波センサーを使っている理由は、**コストパフォーマンスや主な焦点である軽量設計**に貢献していること、通常、Lidarセンサーに比べ、カメラや超音波センサーは**低い消費電力**であり、エネルギー効率が良いです。

4. 安定した電力供給と柔軟性：18650電池4本をBuildHatに接続し、電源を供給することにしました。**スイッチを一度オンにするだけ電源を供給することができ、バッテリーの交換や管理が容易に行えるため、柔軟な運用が可能で、負荷の高い処理を実行する際にも安定した電力供給が保たれ、長時間の稼働においても安定性**が保たれることが期待されます。

## ソフトウェア

### 使用OS

私たちは既存のDebian BusterがベースとなったRaspberry Pi OSを使用しています。

### プログラミング言語

私たちのコードはすべて、Pythonで書かれています。

### アルゴリズム

* ### 前提

前提として、カメラの解像度は画像処理に大きく影響します。Pi Camera V2の場合、解像度と画素数は以下の表のようになります。

| 解像度 | 画素数 |
| :--: | :--: |
| 1920 × 1080 | 207万画素 |
| 1280 x 720 | 92万画素 |
| 640 x 480 | 30万画素 |

この表から分かるように、高解像度の場合、データ量が多く、リアルタイムで処理する際に処理に負荷がかかります。Future Engineersでは、3分以内に3周する速度とオブジェクトの認識の精度が求められるため、高解像度であると、処理能力が追いつかず、FPS(フレームレート)が下がり、画像データの更新が遅くなります。Open Challengeでは障害物を避ける必要がなく、壁のみの画像処理と超音波によるP制御より、解像度は640×480とし、Obstacle Challengeでは障害物と壁の画像処理が必要であるため、320×240としています。

* ### OpenChallenge

Open Challengeは、トラックに障害物がなく、中央の壁が変化することにより、セクションにより壁と壁の幅が変化するため、適応しながら、3周をするミッションです。このミッションの達成方法として、以下のアルゴリズムを考えました。

1. 障害物がないため、壁のしきい値の最小値と最大値の範囲を定義し、真ん中から下部をROI(関心領域)抽出・マスク処理(二値化)をしたあと、そのデータにオープニング処理(ノイズ除去、特徴抽出)を施す。

2. オープニング処理を施した画像の輪郭から壁の最大面積を算出する。

3. 画像の中央（ROI抽出した画像の左側、右側を切り取る）のみにし、中央に表示される壁の面積がある一定の値を超えるまで、ロボットの左右にある超音波センサー(HC-SR04)で左右の壁のちょうど中央になるようにP制御を用いて、トレースをする。

4. 中央に表示される壁の面積がある一定の値を超える条件が満たされた時、壁に近いので、左右の超音波センサーのうち、どちら側が壁からの距離が遠いか比較し、判別する。

5. 壁からの距離が遠い方で時計回りか反時計回りか判別できるので、その判別結果を用いて、時計回りなら右に、反時計回りなら左に曲がるようにステアリングを操作する。(この時、時計回りか反時計回りかを記憶し、２回目以降にその判断結果を用いる)

6. 1.~5.の動作を3周するまで繰り返す。

* ### ObstacleChallenge

Obstacle Challengeは、障害物を避けながら、3周をするミッションです。このミッションの達成方法として以下のアルゴリズムを考えました。

1. 赤色と緑色のしきい値の最小値と最大値の範囲を定義し、マスク処理をしたあと、そのデータにオープニング処理を施す。

2. オープニング処理を施した画像の輪郭から赤色と緑色の最大面積とその面積の重心を算出する。

![detect](https://github.com/washiwashiwashi/assignment/blob/images/img/detect.png)

![content](https://github.com/washiwashiwashi/assignment/blob/images/img/content.jpg)

3. その最大面積を評価し、赤と緑、どちらの面積の方が大きいか、その面積は十分に大きいかという条件を満たすか判定する。(算出された面積が大きければ、大きいほどロボットに近いところにあるといえる)

4. ロボットの目の前にオブジェクトがある時(面積がある一定の値以上の条件)オブジェクトの色に応じて、ステアリングを操作し、回避を行う。

5. ここで、三分割されたマスク画像について、2.で算出された重心が赤なら左側の領域、緑なら右側の領域に入った時、オブジェクトは回避できたと判断する。

6. 4.、5.の間にかかった時間（回避に要した時間)を算出しておき、それを元に今度は逆向きにステアリングを操作し、ロボットを元の位置に戻す。

7. 1.~6.の動作を3周するまで繰り返す。
