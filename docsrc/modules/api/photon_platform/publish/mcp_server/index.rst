photon_platform.publish.mcp_server
==================================

.. py:module:: photon_platform.publish.mcp_server

.. autoapi-nested-parse::

   Zero-dependency MCP stdio server for ``photon-platform/publish`` (``publish mcp``).

   Supports both ``Content-Length`` framed and newline-delimited JSON-RPC 2.0 over stdio
   on Python 3.13, keeping Sphinx and extensions warm in-process while returning compact,
   noise-free JSON summaries for incremental HTML builds, batch builds, EPUB 3 builds,
   and primary-source folio link audits.



Attributes
----------

.. autoapisummary::

   photon_platform.publish.mcp_server.TOOL_REGISTRY


Functions
---------

.. autoapisummary::

   photon_platform.publish.mcp_server.publish_build
   photon_platform.publish.mcp_server.publish_build_batch
   photon_platform.publish.mcp_server.publish_clean
   photon_platform.publish.mcp_server.publish_epub
   photon_platform.publish.mcp_server.publish_folio_links
   photon_platform.publish.mcp_server.read_rpc_message
   photon_platform.publish.mcp_server.write_rpc_message
   photon_platform.publish.mcp_server.handle_rpc_request
   photon_platform.publish.mcp_server.run_stdio_jsonrpc
   photon_platform.publish.mcp_server.call_mcp_stdio
   photon_platform.publish.mcp_server.main


Module Contents
---------------

.. py:function:: publish_build(repo: str, clean: bool = False, jobs: int | None = None) -> dict[str, Any]

   Build Sphinx HTML documentation for ``repo`` (incremental by default).


.. py:function:: publish_build_batch(repos: list[str], clean: bool = False, jobs: int | None = None) -> dict[str, Any]

   Build Sphinx HTML documentation across multiple repositories in a warm process.


.. py:function:: publish_clean(repo: str) -> dict[str, Any]

   Remove ``docs/`` and generated ``docsrc/modules/api/`` for ``repo``.


.. py:function:: publish_epub(repo: str, book: str | None = None, output: str | None = None) -> dict[str, Any]

   Build EPUB 3 edition(s) for ``repo``.


.. py:function:: publish_folio_links(repo: str, optimize_scans: bool = False, grayscale: bool = False) -> dict[str, Any]

   Audit ``.. folio::`` directives and ``:folio:`` badges for ``repo``.


.. py:data:: TOOL_REGISTRY
   :type:  dict[str, tuple[collections.abc.Callable[..., dict[str, Any]], dict[str, Any]]]

.. py:function:: read_rpc_message(stream: BinaryIO) -> tuple[dict[str, Any] | None, str]

   Read one JSON-RPC message supporting both Content-Length framing and line-delimited JSON.


.. py:function:: write_rpc_message(stream: BinaryIO, payload: dict[str, Any], mode: str = 'line') -> None

   Write a JSON-RPC response matching the client's framing mode.


.. py:function:: handle_rpc_request(msg: dict[str, Any]) -> dict[str, Any] | None

   Process one JSON-RPC 2.0 request dictionary and return a response dictionary.


.. py:function:: run_stdio_jsonrpc() -> None

   Run the MCP JSON-RPC 2.0 server loop over standard input/output.


.. py:function:: call_mcp_stdio(tool_name: str, arguments: dict[str, Any], server_cmd: list[str] | None = None, env: dict[str, str] | None = None) -> dict[str, Any]

   Execute a full MCP stdio JSON-RPC handshake + ``tools/call`` for tests and CLI.


.. py:function:: main() -> None

   Entry point for ``publish-mcp`` / ``publish mcp`` stdio server.


