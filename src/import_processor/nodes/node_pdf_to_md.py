from src.import_processor.base import BaseNode
from src.import_processor.state import ImportGraphState
import os
from dotenv import load_dotenv
load_dotenv()


class NodePDFToMD(BaseNode):
    """
    PDF 转 Markdown 节点：PDF结构化解析
    """

    name = "node_pdf_to_md"


    def process(self, state: ImportGraphState):
        """
        :param state: `pdf_path`、`file_dir`
        :return: `md_path`、`md_content`
        """

        # 步骤1：校验PDF路径和输出目录
        pdf_path_obj, output_dir_obj = self._step_1_validate_paths(state)

        # 步骤2：上传PDF至MinerU并轮询解析结果
        zip_url = self._step_2_upload_and_poll(pdf_path_obj)

        # 步骤3：下载ZIP包并提取MD文件

        # 步骤4：读取md的内容

        # 步骤5：更新state状态
        return state
    def _step_1_validate_paths(self, state: ImportGraphState):
        """
        步骤1：校验PDF文件路径和输出目录
        核心职责：参数非空校验 | 路径转换 | PDF文件有效性校验 | 输出目录自动创建
        返回：合法的PDF文件Path对象、输出目录Path对象
        异常：ValueError(参数缺失)、FileNotFoundError(文件无效)
        """

        # 1、参数非空校验
        pdf_path = state.get("pdf_path")
        if not pdf_path:
            raise StateFieldError(field_name='pdf_path', expected_type=str)

        file_dir = state.get("file_dir")
        if not file_dir:
            raise StateFieldError(field_name='file_dir', expected_type=str)

        # 2、转换为Path对象统一处理路径
        pdf_path_obj = Path(pdf_path)
        file_dir_obj = Path(file_dir)

        # 3、PDF文件有效性校验
        if not pdf_path_obj.exists():
            raise FileProcessingError(message=f"PDF文件{pdf_path_obj.name}不存在")

        # 4、确保输出目录存在，不存在则递归创建
        if not file_dir_obj.exists():
            self.logger.info(f"输出目录不存在，自动创建：{file_dir_obj.absolute()}")
            file_dir_obj.mkdir(parents=True, exist_ok=True)

        return pdf_path_obj, file_dir_obj
    def _step_2_upload_and_poll(self, pdf_path_obj: Path):
        """
        步骤2：上传PDF至MinerU并轮询解析任务状态
        核心流程：配置校验 → 获取上传链接 → 文件上传 → 任务轮询（直至完成/失败/超时）
        参数：pdf_path_obj-已校验的PDF Path对象
        返回：解析结果ZIP包下载链接full_zip_url
        异常：ValueError(配置缺失)、RuntimeError(请求/上传失败)、TimeoutError(任务超时)
        """
        base_url=os.getenv("MINERU_BASE_URL"),
        api_token=os.getenv("MINERU_API_TOKEN")
        # 1、配置文件校验
        if not base_url:
            raise ConfigurationError("MinerU配置缺失：请在 .env 文件中正确配置 MINERU_BASE_URL 参数")
        if not api_token:
            raise ConfigurationError("MinerU配置缺失：请在 .env 文件中正确配置 MINERU_API_TOKEN 参数")

        # 2、从MinerU服务器获取上传链接
        token = api_token
        url = f"{base_url}/file-urls/batch"
        header = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        data = {
            "files": [
                {"name": pdf_path_obj.name}
            ],
            "model_version": "vlm"
        }

        # 获取上传url和任务的batch_id
        response = requests.post(url, headers=header, json=data)

        # 对响应结果进行校验
        # 先校验http状态
        if response.status_code != 200:
            raise PdfConversionError(message=f"获取上传链接响应失败：状态码：{response.status_code}，响应结果：{response}")

        # 校验业务码
        result = response.json()
        if result.get("code") != 0:
            raise PdfConversionError(f"获取上传链接失败：返回数据：{result}")

        # 获取响应结果
        signed_url = result["data"]["file_urls"][0]
        batch_id = result["data"]["batch_id"]

        # 3、文件上传
        with open(pdf_path_obj, "rb") as f:
            res_upload = requests.put(signed_url, data=f)
            if res_upload.status_code != 200:
                raise PdfConversionError(f"文件上传失败：状态码：{res_upload.status_code}，响应结果：{res_upload}")

            self.logger.info(f"文件上传成功！")

        # 4、批量获取任务结果
        poll_url = f"{base_url}/extract-results/batch/{batch_id}"

        start_time = time.time()  # 记录开始时间
        timeout_seconds = 600  # 最大超时时间
        poll_interval = 3  # 轮询间隔时间
        self.logger.info(f"【任务轮询】最大超时：{timeout_seconds}s，batch_id：{batch_id}")

        # 根据batch_id轮询任务状态直到成功"done"
        while True:
            # 已消耗时间
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout_seconds:
                raise TimeoutError(f"【任务轮询】超时！任务处理超{timeout_seconds}秒，batch_id：{batch_id}")

            # 发起轮询请求，短超时10秒，异常则重试
            try:
                res_poll = requests.get(url=poll_url, headers=header, timeout=10)
            except Exception as e:
                self.logger.warning(f"【任务轮询】网络请求异常，{poll_interval}秒后重试：{str(e)}，bactch_id：{batch_id}")
                time.sleep(poll_interval)
                continue

            # 处理HTTP响应错误
            if res_poll.status_code != 200:
                raise PdfConversionError(f"【任务轮询】HTTP请求失败，状态码：{res_poll.status_code}，响应内容：{res_poll}")

            # 解析轮询结果，校验业务状态
            poll_data = res_poll.json()
            if poll_data["code"] != 0:
                raise PdfConversionError(f"【任务轮询】业务错误，返回数据：{poll_data}")

            extract_results = poll_data["data"]["extract_result"]

            # 获取结果
            result_item = extract_results[0]
            data_state = result_item["state"]

            # 状态为 done
            if data_state == "done":
                self.logger.info(f"【任务轮询】解析任务完成！总耗时{int(elapsed_time)}s，bactch_id：{batch_id}")

                full_zip_url = result_item["full_zip_url"]
                self.logger.info(f"【任务轮询】返回ZIP包下载链接：{full_zip_url}，bactch_id：{batch_id}")

                return full_zip_url

            elif data_state == "failed":
                err_msg = result_item.get("err_msg", "未知错误，无具体信息")
                raise PdfConversionError(f"【任务轮询】解析任务失败！batch_id：{batch_id}，错误信息：{err_msg}")

            else:
                self.logger.info(f"【任务轮询】处理中... 已耗时{int(elapsed_time)}s，状态：{data_state}， batch_id：{batch_id}")
                time.sleep(poll_interval)